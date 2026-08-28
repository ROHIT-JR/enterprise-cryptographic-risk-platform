import { describe, expect, it } from "vitest";
import { formatNumber } from "./format";

describe("formatNumber", () => {
  it("formats small inventory counts without compact notation", () => {
    expect(formatNumber(128)).toBe("128");
  });
});

