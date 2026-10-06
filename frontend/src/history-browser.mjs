export const HISTORY_METRICS = {
  compressor: [
    { key: "hp_1st", label: "HP 1st", unit: "" }, { key: "lp_1st", label: "LP 1st", unit: "" },
    { key: "hp_2nd", label: "HP 2nd", unit: "" }, { key: "lp_2nd", label: "LP 2nd", unit: "" },
    { key: "temperature_hi", label: "Temperature High", unit: "°C" },
    { key: "temperature_lo", label: "Temperature Low", unit: "°C" },
    { key: "valve", label: "Valve", unit: "" }, { key: "busy", label: "Busy", unit: "state" },
  ],
  vacuum: [
    { key: "temperature_c", label: "Temperature", unit: "°C" },
    { key: "pressure_kpa", label: "Estimated Pressure", unit: "kPa" },
    { key: "current_a", label: "Current", unit: "A" }, { key: "vibration", label: "Vibration", unit: "mm/s" },
    { key: "accel_x", label: "Accel X", unit: "g" }, { key: "accel_y", label: "Accel Y", unit: "g" },
    { key: "accel_z", label: "Accel Z", unit: "g" },
  ],
};
export const sourceName = source => source === "compressor" ? "Compressor" : "Vacuum Pump";
export function historySource(module) {
  if (/^compressor-m[1-8]$/.test(module?.module_code) && module.telemetry_source === "compressor" && module.source_device_key != null) return "compressor";
  if (module?.module_code === "vacuum-pump" && module.telemetry_source === "vacuum" && module.source_device_key != null) return "vacuum";
  return null;
}
export function machineModules(device) {
  // OFF is a current operating state, not an absence of historical telemetry.
  return (device?.modules || []).filter(historySource).sort((a, b) => a.module_code.localeCompare(b.module_code, undefined, { numeric: true }));
}
export const seriesKey = (device, module) => `${device.id}:${module.id}`;
export function numeric(value) {
  return value == null || value === "" || !Number.isFinite(Number(value)) ? null : Number(value);
}
export function sourceTime(value) {
  if (!value) return NaN;
  const text = String(value).replace(" ", "T");
  return Date.parse(/[zZ]$|[+-]\d{2}:?\d{2}$/.test(text) ? text : `${text}+07:00`);
}
export function localInput(stamp) {
  return new Date(stamp + 7 * 3600_000).toISOString().slice(0, 16);
}
export function initialWindow(now = Date.now()) {
  const today = localInput(now).slice(0, 10);
  const first = sourceTime(`${today}T00:00`);
  return { mode: "custom", start: localInput(first), end: localInput(first + 24 * 3600_000) };
}
export function windowError(window) {
  if (window.mode === "latest") return "";
  const start = sourceTime(window.start), end = sourceTime(window.end);
  if (!Number.isFinite(start) || !Number.isFinite(end)) return "Select both start and end date/time";
  if (end <= start) return "End time must be after start time";
  if (end - start > 31 * 24 * 3600_000) return "Choose up to 31 days at a time";
  return "";
}
export function windowParams(window) {
  const error = windowError(window);
  if (error) throw new Error(error);
  return window.mode === "latest" ? {} : { start: `${window.start}+07:00`, end: `${window.end}+07:00` };
}
export function presetWindow(window, hours) {
  const end = sourceTime(window.end);
  return { ...window, mode: "custom", start: localInput(end - hours * 3600_000) };
}
export function metricChoices(series) {
  return [...new Set(series.map(item => historySource(item.module)))].filter(Boolean).flatMap(source =>
    HISTORY_METRICS[source].map(metric => ({ ...metric, source, id: `${source}:${metric.key}` })));
}
export async function boundedMap(items, workers, callback, signal) {
  let next = 0;
  const output = new Array(items.length);
  await Promise.all(Array.from({ length: Math.min(workers, items.length) }, async () => {
    while (!signal.aborted && next < items.length) {
      const index = next++;
      output[index] = await callback(items[index]);
    }
  }));
  return output;
}
