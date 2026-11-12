import React from "react";
import type { MockSpec } from "./theme";
import { Terminal } from "./mocks/Terminal";
import { CommentBox } from "./mocks/CommentBox";
import { Checklist } from "./mocks/Checklist";
import { BrowserMock } from "./mocks/BrowserMock";
import { FileExtract } from "./mocks/FileExtract";
import { WindowRows } from "./mocks/WindowRows";

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
    default:
      return <WindowRows at={at} title={mock.title} items={mock.items} times={times} />;
  }
};
