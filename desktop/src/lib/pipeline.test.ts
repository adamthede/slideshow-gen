import { describe, it, expect } from "vitest";
import {
  PIPELINE_STEPS,
  phaseToStepIndex,
  computePhaseEtaSeconds,
  formatEta,
} from "./pipeline";

describe("PIPELINE_STEPS", () => {
  it("defines exactly the four user-facing steps in order", () => {
    expect(PIPELINE_STEPS.map((s) => s.key)).toEqual([
      "discovery",
      "clips",
      "batching",
      "composite",
    ]);
  });
});

describe("phaseToStepIndex", () => {
  it("maps discovery-family engine phases to step 0", () => {
    expect(phaseToStepIndex("discovery")).toBe(0);
    expect(phaseToStepIndex("deduplication")).toBe(0);
  });

  it("maps clip-rendering engine phases to step 1", () => {
    expect(phaseToStepIndex("images")).toBe(1);
    expect(phaseToStepIndex("static-batching")).toBe(1);
  });

  it("maps batch-reduction engine phases to step 2", () => {
    expect(phaseToStepIndex("batching")).toBe(2);
    expect(phaseToStepIndex("chunking")).toBe(2);
  });

  it("maps compositing to step 3", () => {
    expect(phaseToStepIndex("compositing")).toBe(3);
  });

  it("returns null for unknown or absent phases", () => {
    expect(phaseToStepIndex("nonsense")).toBeNull();
    expect(phaseToStepIndex(null)).toBeNull();
  });
});

describe("computePhaseEtaSeconds", () => {
  it("extrapolates remaining time from the observed rate", () => {
    // 50 of 200 done in 10s → 5/s → 150 remaining → 30s
    expect(
      computePhaseEtaSeconds({ done: 50, total: 200, phaseElapsedS: 10 }),
    ).toBeCloseTo(30, 5);
  });

  it("returns 0 once the phase is complete", () => {
    expect(
      computePhaseEtaSeconds({ done: 200, total: 200, phaseElapsedS: 40 }),
    ).toBe(0);
    expect(
      computePhaseEtaSeconds({ done: 201, total: 200, phaseElapsedS: 40 }),
    ).toBe(0);
  });

  it("returns null when there is not enough data to estimate", () => {
    expect(
      computePhaseEtaSeconds({ done: 0, total: 200, phaseElapsedS: 10 }),
    ).toBeNull();
    expect(
      computePhaseEtaSeconds({ done: 50, total: 0, phaseElapsedS: 10 }),
    ).toBeNull();
    expect(
      computePhaseEtaSeconds({ done: 50, total: 200, phaseElapsedS: 0 }),
    ).toBeNull();
  });

  it("guards against non-finite inputs", () => {
    expect(
      computePhaseEtaSeconds({ done: NaN, total: 200, phaseElapsedS: 10 }),
    ).toBeNull();
    expect(
      computePhaseEtaSeconds({
        done: 50,
        total: 200,
        phaseElapsedS: Infinity,
      }),
    ).toBeNull();
  });
});

describe("formatEta", () => {
  it("formats sub-minute values in seconds", () => {
    expect(formatEta(45)).toBe("~45s");
    expect(formatEta(0)).toBe("~0s");
  });

  it("formats minute values, dropping a zero seconds remainder", () => {
    expect(formatEta(100)).toBe("~1m 40s");
    expect(formatEta(120)).toBe("~2m");
  });

  it("formats hour values, dropping a zero minutes remainder", () => {
    expect(formatEta(3600)).toBe("~1h");
    expect(formatEta(7500)).toBe("~2h 5m");
  });

  it("returns null for null, negative, or non-finite input", () => {
    expect(formatEta(null)).toBeNull();
    expect(formatEta(-5)).toBeNull();
    expect(formatEta(Infinity)).toBeNull();
  });
});
