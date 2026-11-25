import React from "react";
import type { MockSpec } from "./theme";
import { Terminal } from "./mocks/Terminal";
import { CommentBox } from "./mocks/CommentBox";
import { Checklist } from "./mocks/Checklist";
import { BrowserMock } from "./mocks/BrowserMock";
import { FileExtract } from "./mocks/FileExtract";
import { WindowRows } from "./mocks/WindowRows";
import { ChatCard, MapsCard, GaugeCard } from "./mocks/ProofCards";
import { WidgetsFx, BillFx, StampFx, TierFx, WallFx, PhoneFanFx, PullbackFx, CountdownFx, KeyRainFx, ViewfinderFx, LockOnFx, RabbitFx, GiantFx, CollageFx } from "./mocks/FxMocks";
import { TrackerCard, FollowCard, StickersCard, ProofShot } from "./mocks/RefMocks";

// Picks the mock-up component for `mock.type`.
export const MockHost: React.FC<{ mock: MockSpec; at: number; times: number[] }> = ({ mock, at, times }) => {
  switch (mock.type) {
    case "terminal":
      return <Terminal at={at} title={mock.title} items={mock.items} times={times} />;
    case "comment":
      return <CommentBox at={at} text={mock.items[0] ?? ""} typeAt={times[0] ?? at + 0.4} pressAt={mock.pressAt ?? (times[0] ?? at) + 2} />;
    case "checklist":
      return <Checklist at={at} title={mock.title} items={mock.items} times={times} />;
    case "browser":
      return <BrowserMock at={at} items={mock.items} times={times} />;
    case "file":
      return <FileExtract at={at} items={mock.items} times={times} />;
    case "chat":
      return <ChatCard at={at} title={mock.title} items={mock.items} times={times} />;
    case "maps":
      return <MapsCard at={at} items={mock.items} times={times} />;
    case "gauge":
      return <GaugeCard at={at} items={mock.items} times={times} />;
    case "tracker":
      return <TrackerCard at={at} title={mock.title} items={mock.items} times={times} />;
    case "follow":
      return <FollowCard at={at} title={mock.title} items={mock.items} times={times} />;
    case "proof":
      return <ProofShot at={at} items={mock.items} times={times} />;
    case "stickers":
      return <StickersCard at={at} items={mock.items} times={times} />;
    case "widgets":
      return <WidgetsFx at={at} title={mock.title} items={mock.items} times={times} />;
    case "bill":
      return <BillFx at={at} title={mock.title} items={mock.items} times={times} />;
    case "stamp":
      return <StampFx at={at} title={mock.title} items={mock.items} times={times} />;
    case "tier":
      return <TierFx at={at} title={mock.title} items={mock.items} times={times} />;
    case "wall":
      return <WallFx at={at} title={mock.title} items={mock.items} times={times} />;
    case "phonefan":
      return <PhoneFanFx at={at} title={mock.title} items={mock.items} times={times} />;
    case "pullback":
      return <PullbackFx at={at} title={mock.title} items={mock.items} times={times} />;
    case "countdown":
      return <CountdownFx at={at} title={mock.title} items={mock.items} times={times} />;
    case "keyrain":
      return <KeyRainFx at={at} title={mock.title} items={mock.items} times={times} />;
    case "viewfinder":
      return <ViewfinderFx at={at} title={mock.title} items={mock.items} times={times} />;
    case "lockon":
      return <LockOnFx at={at} title={mock.title} items={mock.items} times={times} />;
    case "rabbit":
      return <RabbitFx at={at} title={mock.title} items={mock.items} times={times} />;
    case "giant":
      return <GiantFx at={at} title={mock.title} items={mock.items} times={times} />;
    case "collage":
      return <CollageFx at={at} title={mock.title} items={mock.items} times={times} />;
    default:
      return <WindowRows at={at} title={mock.title} items={mock.items} times={times} />;
  }
};
