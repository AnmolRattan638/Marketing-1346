from viralsim.audience import AudiencePool
from viralsim.schema import DIMS, Content

_POOL = None


def pool() -> AudiencePool:
    global _POOL
    if _POOL is None:
        _POOL = AudiencePool.synthetic(8000, seed=1)
    return _POOL


def content(q: float, topics=("comedy",), **kw) -> Content:
    return Content(dims={d: q for d in DIMS}, topics={t: 1.0 for t in topics}, **kw).ensure_composites()
