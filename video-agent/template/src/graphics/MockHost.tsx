import React from "react";
import type { MockSpec } from "./theme";
import { Terminal } from "./mocks/Terminal";
import { CommentBox } from "./mocks/CommentBox";
import { Checklist } from "./mocks/Checklist";
import { BrowserMock } from "./mocks/BrowserMock";
import { FileExtract } from "./mocks/FileExtract";
import { WindowRows } from "./mocks/WindowRows";
import { ChatCard, MapsCard, GaugeCard } from "./mocks/ProofCards";
import { TrackerCard, FollowCard, StickersCard } from "./mocks/RefMocks";

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
    case "stickers":
      return <StickersCard at={at} items={mock.items} times={times} />;
    default:
      return <WindowRows at={at} title={mock.title} items={mock.items} times={times} />;
  }
};
