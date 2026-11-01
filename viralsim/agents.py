"""Hybrid agent simulation: a few LLM-driven *core* agents (with memory, relationships and
role-specific incentives) interact with many cheap *ordinary* agents driven by persona-grounded
behaviour models. Combines HiSim's core/ordinary split, PhantomCrowd's memory + crowd pulse +
interviews and Viralix's role swarms. Without an LLM, core agents fall back to the same behaviour
model, so the simulator always runs offline."""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field

import numpy as np

from .audience import AudiencePool
from .creator import Creator
from .engagement import engage_all
from .llm import LLMClient, extract_json
from .metrics import cascade_metrics
from .risk import discourse_tension
from .schema import TOPICS, Content
from .trends import TrendSnapshot

ACTIONS = ("post", "reply", "share", "like", "dislike", "ignore")

ROLES = {  # role -> (description, share_bias, dislike_bias, comment_bias)
    "public": ("an ordinary social-media user reacting naturally", 1.0, 1.0, 1.0),
    "influencer": ("an influencer who amplifies content that grows their audience and drops risky content", 2.0, 0.8, 1.3),
    "brand": ("a brand manager who cares about reputation and avoids controversy", 0.6, 1.6, 0.8),
    "academic": ("an analyst/academic who is sceptical and asks for evidence", 0.5, 1.4, 1.6),
    "competitor": ("a competitor looking for weaknesses and counter-narratives", 0.4, 2.0, 1.4),
    "creator": ("a peer creator who engages with posts in their niche", 1.2, 0.8, 1.2),
}


@dataclass
class RelationshipMemory:
    interactions: int = 0
    sentiment_toward: float = 0.0
    last_action: str = ""


@dataclass
class AgentMemory:
    my_posts: list[str] = field(default_factory=list)
    seen: list[dict] = field(default_factory=list)
    relationships: dict[str, RelationshipMemory] = field(default_factory=dict)
    sentiment_history: list[dict] = field(default_factory=list)

    def record(self, rnd: int, act: dict) -> None:
        if act["action"] in ("post", "reply") and act.get("content"):
            self.my_posts.append(act["content"][:200])
            self.my_posts = self.my_posts[-5:]
        tgt = act.get("target")
        if tgt:
            rel = self.relationships.setdefault(tgt, RelationshipMemory())
            rel.interactions += 1
            rel.last_action = act["action"]
            if act["action"] in ("like", "share", "reply"):
                rel.sentiment_toward = min(1.0, rel.sentiment_toward + 0.2)
            elif act["action"] == "dislike":
                rel.sentiment_toward = max(-1.0, rel.sentiment_toward - 0.3)
        self.sentiment_history.append({"round": rnd, "score": act.get("sentiment_score", 0.0)})

    def see(self, name: str, content: str, rnd: int) -> None:
        self.seen = (self.seen + [{"agent": name, "content": content[:160], "round": rnd}])[-12:]

    def prompt(self) -> str:
        if not (self.my_posts or self.seen):
            return "No memory yet: this is your first interaction."
        parts = []
        if self.my_posts:
            parts.append("Your earlier posts: " + " | ".join(self.my_posts[-3:]))
        if self.seen:
            parts.append("You recently saw: " + " | ".join(f"@{s['agent']}: {s['content']}" for s in self.seen[-4:]))
        strong = [(n, r) for n, r in self.relationships.items() if abs(r.sentiment_toward) >= 0.3]
        if strong:
            parts.append("Relationships: " + ", ".join(f"@{n} ({'friendly' if r.sentiment_toward > 0 else 'hostile'})" for n, r in strong[:4]))
        return "\n".join(parts)


@dataclass
class Agent:
    id: int
    name: str
    persona_idx: int
    role: str
    core: bool
    age: int
    interests: list[str]
    memory: AgentMemory = field(default_factory=AgentMemory)


@dataclass
class HybridResult:
    actions: list[dict]
    rounds: list[dict]
    totals: dict
    sentiment: dict
    by_role: dict
    engagement_rate: float
    cascade: dict
    discourse_tension: dict
    agents: list[Agent]

    def summary(self) -> dict:
        return {"totals": self.totals, "sentiment": self.sentiment, "by_role": self.by_role,
                "engagement_rate": round(self.engagement_rate, 4), "cascade": self.cascade,
                "discourse_tension": self.discourse_tension, "rounds": self.rounds}


def _label(score: float) -> str:
    return "positive" if score > 0.25 else "negative" if score < -0.25 else "neutral"


def _behaviour(a: Agent, pe, i: int, exposed: bool, rng, role_b) -> dict:
    """Persona-grounded action sampling (the ABM used for ordinary agents and as the offline core policy)."""
    if not exposed or rng.random() > pe.watch[i]:
        return {"action": "ignore", "sentiment_score": 0.0}
    share_b, dis_b, com_b = role_b
    match, interest = float(pe.match[i]), float(pe.interest[i])
    score = float(np.clip(1.6 * match + 0.5 * interest, -1, 1))
    p_dis = min(0.9, dis_b * 0.6 * max(0.0, -match) * (0.5 + 0.5 * (1 - pe.watch[i])))
    p_share, p_com, p_like = min(0.9, pe.share[i] * share_b * 4), min(0.9, pe.comment[i] * com_b * 4), min(0.95, pe.like[i] * 2.5)
    r = rng.random()
    if r < p_dis:
        return {"action": "dislike", "sentiment_score": round(min(score, -0.3), 2)}
    if rng.random() < p_share:
        return {"action": "share", "sentiment_score": round(max(score, 0.1), 2)}
    if rng.random() < p_com:
        return {"action": "reply", "sentiment_score": round(score, 2)}
    if rng.random() < p_like:
        return {"action": "like", "sentiment_score": round(max(score, 0.1), 2)}
    return {"action": "ignore", "sentiment_score": round(score * 0.3, 2)}


def _core_prompt(a: Agent, content: Content, feed: list[dict], pulse: str) -> tuple[str, str]:
    desc = ROLES[a.role][0]
    system = (f"You are simulating a real person on social media: @{a.name}, age {a.age}, interested in "
              f"{', '.join(a.interests) or 'various topics'}. Role: {desc}. Stay in character; opinions may evolve.\n"
              f"MEMORY:\n{a.memory.prompt()}\n"
              'Reply with JSON only: {"action":"post|reply|share|like|dislike|ignore","content":"<=240 chars","sentiment":"positive|negative|neutral|mixed","sentiment_score":-1..1}')
    lines = "\n".join(f"@{x['agent']}: {x['content']}" for x in feed[-8:] if x.get("content"))
    user = f"Content you just saw:\n'''{content.text}'''\n{pulse}\nRecent feed:\n{lines or '(empty)'}\nWhat do you do?"
    return system, user


def run_hybrid(content: Content, pool: AudiencePool, *, creator: Creator | None = None, trend: TrendSnapshot | None = None,
               llm: LLMClient | None = None, n_core: int = 12, n_ordinary: int = 600, rounds: int = 6,
               roles: dict[str, float] | None = None, seed: int = 0) -> HybridResult:
    rng = np.random.default_rng(seed)
    trend = trend or TrendSnapshot.neutral()
    pe = engage_all(pool, content, trend.alignment(content))
    roles = roles or {"public": .5, "influencer": .12, "creator": .12, "brand": .08, "academic": .1, "competitor": .08}
    rn, rp = list(roles), np.array(list(roles.values())) / sum(roles.values())
    idx = rng.choice(len(pool), n_core + n_ordinary, replace=False)
    agents = []
    for k, i in enumerate(idx):
        top = [TOPICS[j] for j in np.argsort(-pool.interests[i])[:3] if pool.interests[i, j] > 0]
        core = k < n_core
        agents.append(Agent(k + 1, f"user{k + 1}", int(i), str(rng.choice(rn, p=rp)) if core else "public", core, int(pool.age[i]), top))
    N = len(agents)
    seen = np.zeros(N, dtype=bool)
    actions, round_stats, feed = [], [], []
    parent, step_of = {0: None}, {0: 0}
    prev = Counter()
    for rnd in range(1, rounds + 1):
        p_see = min(0.9, 0.12 + 3.0 * prev["share"] / N + 0.6 * prev["like"] / N)
        pulse = (f"CROWD PULSE last round: {prev['like']} liked, {prev['share']} shared, {prev['reply']} replied, "
                 f"{prev['dislike']} disliked." if rnd > 1 else "")
        cur = Counter()
        for a in agents:
            if seen[a.id - 1] and rnd > 1 and rng.random() > 0.5 + 0.3 * pool.activity[a.persona_idx]:
                continue                                      # already reacted; most agents move on
            exposed = seen[a.id - 1] or rng.random() < p_see * (0.5 + pool.activity[a.persona_idx])
            if not exposed:
                continue
            first_time = not seen[a.id - 1]
            seen[a.id - 1] = True
            act = None
            if a.core and llm is not None and (first_time or rnd % 2 == 0):
                try:
                    s, u = _core_prompt(a, content, feed, pulse)
                    d = extract_json(llm.complete(s, u, json_mode=True, temperature=0.7))
                    if d.get("action") in ACTIONS:
                        act = {"action": d["action"], "content": str(d.get("content", ""))[:240],
                               "sentiment_score": float(np.clip(float(d.get("sentiment_score", 0)), -1, 1))}
                except Exception:
                    act = None
            if act is None:
                if not first_time:
                    continue
                act = _behaviour(a, pe, a.persona_idx, True, rng, ROLES[a.role][1:])
            act.update(round=rnd, agent=a.name, agent_id=a.id, role=a.role, core=a.core)
            act["sentiment"] = _label(act.get("sentiment_score", 0.0))
            sharers = [x["agent_id"] for x in actions if x["action"] == "share"]
            if act["action"] in ("share", "reply", "post") and feed and a.core:
                tgt = feed[int(rng.integers(max(0, len(feed) - 5), len(feed)))]
                act["target"] = tgt["agent"]
            if act["action"] == "share":
                parent[a.id] = int(rng.choice(sharers)) if sharers and rng.random() < 0.6 else 0
                step_of[a.id] = rnd
            a.memory.record(rnd, act)
            for b in agents[: n_core]:
                if b.id != a.id and act.get("content") and rng.random() < 0.5:
                    b.memory.see(a.name, act["content"], rnd)
            if act.get("content"):
                feed.append({"agent": a.name, "content": act["content"]})
            actions.append(act)
            cur[act["action"]] += 1
        prev = cur
        round_stats.append({"round": rnd, "new_viewers": int(seen.sum()), **{k: cur[k] for k in ACTIONS}})
    engaged = [x for x in actions if x["action"] != "ignore"]
    totals = Counter(x["action"] for x in actions)
    sent = Counter(x["sentiment"] for x in engaged)
    by_role = defaultdict(lambda: {"n": 0, "avg_sentiment": 0.0, "share_rate": 0.0})
    for x in engaged:
        r = by_role[x["role"]]
        r["n"] += 1
        r["avg_sentiment"] += x["sentiment_score"]
        r["share_rate"] += x["action"] == "share"
    for r in by_role.values():
        r["avg_sentiment"] = round(r["avg_sentiment"] / r["n"], 3)
        r["share_rate"] = round(r["share_rate"] / r["n"], 3)
    return HybridResult(actions, round_stats, dict(totals), dict(sent), dict(by_role), len(engaged) / max(1, int(seen.sum())),
                        cascade_metrics(parent, step_of), discourse_tension(actions), agents)


def interview(agent: Agent, content: Content, llm: LLMClient, question: str = "Why did you react the way you did?") -> str:
    """Ask a simulated agent to explain its reaction (needs a real LLM to be meaningful)."""
    sys_, _ = _core_prompt(agent, content, [], "")
    sys_ = sys_.split("Reply with JSON only")[0] + "Answer the interviewer in 2-3 sentences, in character."
    return llm.complete(sys_, question, temperature=0.7, max_tokens=200)
