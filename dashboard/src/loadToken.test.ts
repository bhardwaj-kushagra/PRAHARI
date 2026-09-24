import { describe, expect, it } from "vitest";
import { beginLoad, isLatestLoad } from "./store";

describe("latest load wins (release 1.0, second audit)", () => {
  it("only the most recent request may set the source", () => {
    const slow = beginLoad();                     // e.g. presenter key 3: an uncached recording
    const fast = beginLoad();                     // key 5 pressed before it arrived
    expect([isLatestLoad(slow), isLatestLoad(fast)]).toEqual([false, true]);
    const next = beginLoad();                     // anything later supersedes both
    expect([isLatestLoad(fast), isLatestLoad(next)]).toEqual([false, true]);
  });
});
