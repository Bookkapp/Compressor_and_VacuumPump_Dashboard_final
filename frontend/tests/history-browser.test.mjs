import test from "node:test";
import assert from "node:assert/strict";
import { boundedMap, initialWindow, machineModules, metricChoices, numeric, presetWindow, sourceTime, windowError, windowParams } from "../src/history-browser.mjs";

test("Machine-specific sources include OFF historical modules and exclude unmapped/foreign ones", () => {
  const device = { modules: [
    { id: 8, module_code: "compressor-m8", telemetry_source: "compressor", source_device_key: "017", status: "OFF" },
    { id: 2, module_code: "compressor-m2", telemetry_source: "compressor", source_device_key: "017" },
    { id: 1, module_code: "vacuum-pump", telemetry_source: "vacuum", source_device_key: "VP017" },
    { id: 9, module_code: "compressor-m9", telemetry_source: "compressor", source_device_key: "017" },
    { id: 10, module_code: "compressor-m1", telemetry_source: "vacuum", source_device_key: "VP017" },
  ] };
  assert.deepEqual(machineModules(device).map(item => item.id), [2, 8, 1]);
  assert.deepEqual(machineModules(undefined), []);
  const metrics = metricChoices(machineModules(device).map(module => ({ module })));
  assert.equal(metrics.length, 15);
  assert.equal(metrics.filter(item => item.source === "compressor").some(item => item.key === "accel_x"), false);
  assert.equal(metrics.filter(item => item.source === "vacuum").some(item => item.key === "hp_1st"), false);
});
test("Date/time controls use Thai source clock even when browser timezone differs", () => {
  assert.equal(sourceTime("2026-09-16T18:00:00"), Date.parse("2026-09-16T11:00:00Z"));
  assert.equal(sourceTime("2026-09-16T18:00:00+07:00"), sourceTime("2026-09-16T18:00:00"));
  const window = initialWindow(Date.parse("2026-10-01T19:00:00Z"));
  assert.equal(window.start, "2026-10-02T00:00");
  assert.equal(window.end, "2026-10-03T00:00");
  assert.deepEqual(windowParams(window), { start: "2026-10-02T00:00+07:00", end: "2026-10-03T00:00+07:00" });
  assert.equal(presetWindow(window, 6).start, "2026-10-02T18:00");
  assert.deepEqual(windowParams({ mode: "latest" }), {});
});
test("Invalid or oversized ranges and missing values are not silently substituted", () => {
  for (const window of [{ mode: "custom", start: "", end: "" }, { mode: "custom", start: "2026-09-17T00:00", end: "2026-09-16T00:00" }, { mode: "custom", start: "2026-09-01T00:00", end: "2026-10-03T00:00" }]) {
    assert.ok(windowError(window)); assert.throws(() => windowParams(window));
  }
  assert.equal(numeric(null), null); assert.equal(numeric(""), null); assert.equal(numeric(0), 0);
});
test("Multiple series keep their identity and bounded request concurrency", async () => {
  let active = 0, max = 0;
  const result = await boundedMap(Array.from({ length: 12 }, (_, index) => index), 4, async index => {
    active++; max = Math.max(active, max); await new Promise(resolve => setTimeout(resolve, 3)); active--; return `${index}:own-result`;
  }, new AbortController().signal);
  assert.equal(max, 4); assert.deepEqual(result, Array.from({ length: 12 }, (_, index) => `${index}:own-result`));
});
test("Aborting a stale selection stops starting queued work", async () => {
  const abort = new AbortController(); let calls = 0;
  await boundedMap([1, 2, 3, 4, 5, 6], 2, async index => { calls++; abort.abort(); return index; }, abort.signal);
  assert.equal(calls, 1);
});
