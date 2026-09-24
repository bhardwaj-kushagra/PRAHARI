import { describe, expect, it } from "vitest";
import { ErrorBoundary } from "./components/ErrorBoundary";

describe("ErrorBoundary (release 1.0)", () => {
  it("keeps the error until the recording or tab changes, then tries the view again", () => {
    const err = new Error("boom");
    expect(ErrorBoundary.getDerivedStateFromError(err)).toEqual({ error: err });
    const failed = { error: err, key: "a.gz|signals" };
    expect(ErrorBoundary.getDerivedStateFromProps({ name: "Signals", resetKey: "a.gz|signals", children: null }, failed)).toBeNull();
    expect(ErrorBoundary.getDerivedStateFromProps({ name: "Signals", resetKey: "b.gz|signals", children: null }, failed))
      .toEqual({ error: null, key: "b.gz|signals" });
  });
});
