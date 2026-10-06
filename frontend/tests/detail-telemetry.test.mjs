import test from "node:test";
import assert from "node:assert/strict";
import { COMPRESSOR_SIGNALS, VACUUM_SIGNALS, historyRowsEqual, historyCorrelation, historyRelationship } from "../src/detail-telemetry.mjs";

const rows = [10, 20, 30].map((valve, index) => ({ recorded_at: `2026-09-07T10:${String(index * 5).padStart(2, "0")}:00`, valve, lp_2nd: valve / 5 }));

test("source contracts do not mix Compressor and Vacuum columns", () => {
  assert.ok(COMPRESSOR_SIGNALS.includes("hp_2nd"));
  assert.ok(!COMPRESSOR_SIGNALS.includes("accel_x"));
  assert.ok(VACUUM_SIGNALS.includes("accel_x"));
  assert.ok(!VACUUM_SIGNALS.includes("hp_2nd"));
});

test("Pearson agrees with the backend paired-sample example and uses actual history dates", () => {
  const data = historyCorrelation(rows, ["valve", "lp_2nd"]);
  assert.equal(data.samples, 3);
  assert.equal(data.matrix[0][1], 1);
  assert.deepEqual(data.analysis_window, { from: rows[0].recorded_at, to: rows[2].recorded_at });
  assert.deepEqual(historyRelationship(rows, "valve", "lp_2nd").points[1], { recorded_at: rows[1].recorded_at, x: 20, y: 4 });
  const nonLinear = [1, 2, 3, 4].map((x, index) => ({ recorded_at: String(index), x, y: [1, 2, 5, 4][index] }));
  assert.equal(historyRelationship(nonLinear, "x", "y").correlation, 0.8485);
});

test("missing, non-finite and unpaired samples are excluded, while zero stays valid", () => {
  const data = [{ recorded_at: "1", a: 0, b: 0 }, { recorded_at: "2", a: 1, b: -1 }, { recorded_at: "3", a: 2, b: -2 }, ...[null, "", undefined, Infinity, NaN].map((value, i) => ({ recorded_at: String(i + 4), a: value, b: 900 }))];
  assert.equal(historyRelationship(data, "a", "b").samples, 3);
  assert.equal(historyRelationship(data, "a", "b").correlation, -1);
  assert.equal(historyRelationship(rows.slice(0, 2), "valve", "lp_2nd").correlation, null);
  assert.equal(historyCorrelation(rows.map(row => ({ ...row, valve: 1 })), ["valve", "lp_2nd"]).matrix[0][0], null);
});

test("scatter remains bounded and retains timestamps", () => {
  const data = Array.from({ length: 2000 }, (_, i) => ({ recorded_at: String(i), a: i, b: i * 2 }));
  const result = historyRelationship(data, "a", "b");
  assert.equal(result.samples, 1000);
  assert.equal(result.correlation, 1);
  assert.equal(result.points[1].recorded_at, "2");
});

test("identical polls reuse rows but corrected values at the same timestamp are detected", () => {
  assert.equal(historyRowsEqual(rows, rows.map(row => ({ ...row }))), true);
  assert.equal(historyRowsEqual(rows, rows.map((row, i) => i === 0 ? { ...row, valve: 99 } : row)), false);
  assert.equal(historyRowsEqual(rows, rows.slice(1)), false);
  assert.equal(historyRowsEqual([{ recorded_at: "1", accel_x: null }], [{ recorded_at: "1", accel_x: 0 }]), false);
});
