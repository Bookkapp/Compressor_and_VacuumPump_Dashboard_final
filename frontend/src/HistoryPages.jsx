import React, { useEffect, useMemo, useRef, useState } from "react";
import { HISTORY_METRICS, boundedMap, historySource, initialWindow, machineModules, metricChoices, numeric, presetWindow, seriesKey, sourceName, sourceTime, windowError, windowParams } from "./history-browser.mjs";

const machineName = device => device?.display_name || device?.machine_code || "—";
const formatTime = value => Number.isFinite(sourceTime(value)) ? new Intl.DateTimeFormat("en-GB", { timeZone: "Asia/Bangkok", dateStyle: "short", timeStyle: "medium" }).format(sourceTime(value)) : "—";
const formatNumber = value => numeric(value) === null ? "—" : Number(value).toLocaleString(undefined, { maximumFractionDigits: 3 });
const Empty = ({ children }) => <div className="history-empty">{children}</div>;

function TimeControls({ value, onChange, t }) {
  const error = windowError(value);
  return <fieldset className="history-time-controls">
    <legend>{t("Date and time")}</legend>
    <label>{t("Time Range")}<select value={value.mode} onChange={event => onChange({ ...value, mode: event.target.value })}>
      <option value="custom">{t("Custom date and time")}</option><option value="latest">{t("Latest history")}</option>
    </select></label>
    {value.mode === "latest" && <small>{t("Charts show up to 1,200 newest readings. Choose dates to inspect older periods.")}</small>}
    {value.mode === "custom" && <>
      <label>{t("Start date and time")}<input type="datetime-local" value={value.start} onInput={event => onChange({ ...value, start: event.target.value })} /></label>
      <label>{t("End date and time")}<input type="datetime-local" value={value.end} onInput={event => onChange({ ...value, end: event.target.value })} /></label>
      <div className="history-presets">{[[1, "1 hour"], [6, "6 hours"], [24, "1 day"], [168, "7 days"]].map(([hours, label]) => <button key={hours} type="button" className="ghost-btn" disabled={!Number.isFinite(sourceTime(value.end))} onClick={() => onChange(presetWindow(value, hours))}>{t(label)}</button>)}</div>
      <small>{t("Presets end at the selected end time.")}</small>
      <small>{t("Bangkok time (UTC+7). End time is exclusive. Up to 31 days.")}</small>
      {error && <p className="history-validation" role="alert">{t(error)}</p>}
    </>}
  </fieldset>;
}

function MachineModuleControls({ devices, deviceId, moduleId, onMachine, onModule, t }) {
  const device = devices.find(item => String(item.id) === deviceId);
  const modules = machineModules(device);
  const families = [...new Set(modules.map(historySource))];
  return <div className="history-identity-controls">
    <label>{t("Machine")}<select value={deviceId} onChange={event => onMachine(event.target.value)}>
      <option value="">{t("Select Device")}</option>{devices.filter(item => machineModules(item).length).map(item => <option key={item.id} value={item.id}>{machineName(item)}</option>)}
    </select></label>
    {device && <p className="history-source-note">{t("Available sources")}: <strong>{families.map(sourceName).join(" · ")}</strong></p>}
    <label>{t("Module")}<select value={moduleId} disabled={!device} onChange={event => onModule(event.target.value)}>
      <option value="">{t("Select Module")}</option>{families.map(source => <optgroup key={source} label={sourceName(source)}>{modules.filter(module => historySource(module) === source).map(module => <option key={module.id} value={module.id}>{module.module_name}</option>)}</optgroup>)}
    </select></label>
    {device && !modules.length && <small>{t("No mapped telemetry modules for this machine.")}</small>}
  </div>;
}

function chartOption(series, results, metric) {
  const matching = series.filter(item => historySource(item.module) === metric.source);
  const timeLabel = value => new Intl.DateTimeFormat("en-GB", { timeZone: "Asia/Bangkok", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hourCycle: "h23" }).format(value).replace(", ", "\n");
  return {
    animation: false, backgroundColor: "transparent",
    color: ["#38c3c7", "#4f96d1", "#e3a32b", "#ed5a62", "#8b5cf6", "#42b883"],
    tooltip: { trigger: "axis", confine: true, renderMode: "richText", formatter: params => [formatTime(new Date(params[0]?.value?.[0]).toISOString()), ...params.map(item => `${item.seriesName}: ${formatNumber(item.value[1])}${metric.unit ? ` ${metric.unit}` : ""}`)].join("\n") },
    legend: { type: "scroll", top: 2, left: 8, right: 8, textStyle: { color: "#98a6af", width: 240, overflow: "truncate" }, pageTextStyle: { color: "#98a6af" } },
    grid: { left: 16, right: 18, top: 55, bottom: 78, containLabel: true },
    dataZoom: [{ type: "inside" }, { type: "slider", bottom: 8, height: 18, labelFormatter: timeLabel }],
    xAxis: { type: "time", splitNumber: 3, axisLabel: { color: "#98a6af", fontSize: 11, hideOverlap: true, formatter: timeLabel }, axisLine: { lineStyle: { color: "#293034" } } },
    yAxis: { type: "value", scale: true, ...(['busy','sv'].includes(metric.key) ? {min:0,max:1,interval:1} : {}), name: metric.unit, nameTextStyle: { color: "#98a6af" }, axisLabel: { color: "#98a6af", hideOverlap: true }, splitLine: { lineStyle: { color: "#293034" } } },
    series: matching.map(item => ({ name: `${machineName(item.device)} · ${item.module.module_name}`, type: "line", connectNulls: false, showSymbol: false, smooth: false,
      step: ['busy','sv'].includes(metric.key) ? "end" : undefined,
      data: (results[item.key]?.rows || []).map(row => [sourceTime(row.recorded_at), numeric(row[metric.key])]),
    })),
  };
}

export function HistoricalCharts({ devices, api, notify, t, Chart, analytics = false }) {
  const [deviceId, setDeviceId] = useState("");
  const [moduleId, setModuleId] = useState("");
  const [machineIds, setMachineIds] = useState([]);
  const [moduleKeys, setModuleKeys] = useState([]);
  const [metricIds, setMetricIds] = useState([]);
  const [search, setSearch] = useState("");
  const [window, setWindow] = useState(initialWindow);
  const [request, setRequest] = useState(null);
  const [results, setResults] = useState({});
  const [loading, setLoading] = useState(false);
  const controller = useRef(null);
  const device = devices.find(item => String(item.id) === deviceId);
  const module = machineModules(device).find(item => String(item.id) === moduleId);
  const available = useMemo(() => devices.filter(item => machineIds.includes(item.id)).flatMap(device => machineModules(device).map(module => ({ device, module, key: seriesKey(device, module) }))), [devices, machineIds]);
  const series = analytics ? available.filter(item => moduleKeys.includes(item.key)) : module ? [{ device, module, key: seriesKey(device, module) }] : [];
  const metrics = metricChoices(series);
  const selectedMetrics = metrics.filter(item => metricIds.includes(item.id));
  const invalidate = () => { controller.current?.abort(); setLoading(false); setRequest(null); setResults({}); };
  useEffect(() => () => controller.current?.abort(), []);
  const chooseModule = id => {
    invalidate(); setModuleId(id);
    const chosen = machineModules(device).find(item => String(item.id) === id);
    setMetricIds(chosen ? HISTORY_METRICS[historySource(chosen)].slice(0, 4).map(metric => `${historySource(chosen)}:${metric.key}`) : []);
  };
  const toggleMachine = id => {
    if (!machineIds.includes(id) && machineIds.length >= 6) return;
    invalidate();
    setMachineIds(previous => previous.includes(id) ? previous.filter(item => item !== id) : [...previous, id]);
    setModuleKeys(previous => previous.filter(key => !key.startsWith(`${id}:`)));
  };
  const toggleModule = item => {
    if (!moduleKeys.includes(item.key) && moduleKeys.length >= 12) return;
    invalidate();
    const keys = moduleKeys.includes(item.key) ? moduleKeys.filter(key => key !== item.key) : [...moduleKeys, item.key];
    setModuleKeys(keys);
    const valid = new Set(metricChoices(available.filter(entry => keys.includes(entry.key))).map(metric => metric.id));
    setMetricIds(previous => previous.filter(id => valid.has(id)));
  };
  const toggleMetric = id => {
    if (!metricIds.includes(id) && selectedMetrics.length >= (analytics ? 4 : 8)) return;
    invalidate(); setMetricIds(previous => previous.includes(id) ? previous.filter(item => item !== id) : [...previous.filter(item => metrics.some(metric => metric.id === item)), id]);
  };
  const load = async () => {
    if (!series.length || !selectedMetrics.length || windowError(window)) return;
    controller.current?.abort(); const abort = new AbortController(); controller.current = abort;
    const snapshot = { series: [...series], metrics: [...selectedMetrics], window: { ...window } };
    setRequest(snapshot); setResults({}); setLoading(true);
    try {
      const entries = await boundedMap(snapshot.series, 4, async item => {
        const params = new URLSearchParams({ ...windowParams(snapshot.window), module_id: String(item.module.id), limit: "1200", signals: snapshot.metrics.filter(metric => metric.source === historySource(item.module)).map(metric => metric.key).join(",") });
        // A selected family with no selected metric produces no redundant read.
        if (!params.get("signals")) return [item.key, { rows: [], total: 0 }];
        const data = await api(`/api/devices/${item.device.id}/history-chart?${params}`, { signal: abort.signal });
        if (!Array.isArray(data?.rows)) throw new Error("Invalid telemetry response");
        return [item.key, data];
      }, abort.signal);
      if (!abort.signal.aborted) setResults(Object.fromEntries(entries));
    } catch (error) {
      if (!abort.signal.aborted) { abort.abort(); setLoading(false); setRequest(null); notify("error", t(analytics ? "Analytics" : "Historical Charts"), error.message); }
    } finally { if (!abort.signal.aborted) setLoading(false); }
  };
  const options = useMemo(() => Object.fromEntries((request?.metrics || []).map(metric => [metric.id, chartOption(request.series, results, metric)])), [request, results]);
  const title = analytics ? "Analytics" : "Historical Charts";
  return <>
    <div className="section-title"><div><span className="eyebrow">{t("Data")}</span><h2>{t(title)}</h2></div></div>
    <div className="history-layout">
      <aside className="panel history-controls">
        <div className="panel-head"><h3>{t(analytics ? "Compare machines and modules" : "Select historical data")}</h3></div>
        {analytics ? <>
          <label>{t("Search machines")}<input type="search" value={search} onChange={event => setSearch(event.target.value)} placeholder={t("Search machines")} /></label>
          <fieldset className="history-picker"><legend>1. {t("Machines, up to 6")}</legend><div className="history-picker-scroll">{devices.filter(device => machineModules(device).length && machineName(device).toLowerCase().includes(search.toLowerCase())).map(device => <label className="history-check" key={device.id}><input type="checkbox" checked={machineIds.includes(device.id)} disabled={!machineIds.includes(device.id) && machineIds.length >= 6} onChange={() => toggleMachine(device.id)} /><span>{machineName(device)}<small>{[...new Set(machineModules(device).map(historySource))].map(sourceName).join(" · ")}</small></span></label>)}</div></fieldset>
          <fieldset className="history-picker"><legend>2. {t("Modules, up to 12")}</legend>{!available.length && <small>{t("Select a machine first.")}</small>}<div className="history-picker-scroll">{devices.filter(device => machineIds.includes(device.id)).map(device => <div className="history-module-group" key={device.id}><strong>{machineName(device)}</strong>{[...new Set(machineModules(device).map(historySource))].map(source => <div key={source}><small>{sourceName(source)}</small>{available.filter(item => item.device.id === device.id && historySource(item.module) === source).map(item => <label className="history-check" key={item.key}><input type="checkbox" checked={moduleKeys.includes(item.key)} disabled={!moduleKeys.includes(item.key) && moduleKeys.length >= 12} onChange={() => toggleModule(item)} /><span>{item.module.module_name}</span></label>)}</div>)}</div>)}</div></fieldset>
        </> : <MachineModuleControls devices={devices} deviceId={deviceId} moduleId={moduleId} onMachine={id => { invalidate(); setDeviceId(id); setModuleId(""); setMetricIds([]); }} onModule={chooseModule} t={t} />}
        <fieldset className="history-picker"><legend>{t(analytics ? "Metrics, up to 4" : "Chart signals")}</legend>{!metrics.length && <small>{t("Select a module first.")}</small>}<div className="history-metrics-list">{[...new Set(metrics.map(item => item.source))].map(source => <div key={source} className="history-metric-group"><strong>{sourceName(source)}</strong>{metrics.filter(item => item.source === source).map(metric => <label className="history-check" key={metric.id}><input type="checkbox" checked={metricIds.includes(metric.id)} disabled={!metricIds.includes(metric.id) && selectedMetrics.length >= (analytics ? 4 : 8)} onChange={() => toggleMetric(metric.id)} /><span>{t(metric.label)}</span><small>{metric.unit}</small></label>)}</div>)}</div></fieldset>
        <TimeControls value={window} t={t} onChange={value => { invalidate(); setWindow(value); }} />
        <button className="primary-btn history-load" disabled={loading || !series.length || !selectedMetrics.length || !!windowError(window)} onClick={load}>{t(loading ? "Loading" : "Load charts")}</button>
      </aside>
      <section className="history-results" aria-busy={loading}>
        {request ? <>
          <div className="history-chart-grid">{request.metrics.map(metric => {
            const hasValues = request.series.some(item => historySource(item.module) === metric.source && (results[item.key]?.rows || []).some(row => numeric(row[metric.key]) !== null));
            return <article className="panel" key={metric.id}><div className="panel-head"><h3>{t(metric.label)}</h3><span className="count-pill">{sourceName(metric.source)}{metric.unit ? ` · ${metric.unit}` : ""}</span></div><div className="history-chart-slot">{loading ? <div className="history-chart-skeleton" aria-label={t("Loading")} /> : hasValues ? <Chart option={options[metric.id]} className="chart history-chart" /> : <Empty>{t("No telemetry in the selected range")}</Empty>}</div></article>;
          })}</div>
          {!loading && <>
            {Object.values(results).some(result => result.sampled) && <p className="panel-note">{t("Long ranges use real first and last readings in each time bucket. Brief peaks may be omitted; inspect raw records in Database.")}</p>}
            <article className="panel history-summary"><div className="panel-head"><h3>{t("Sample Summary")}</h3></div><p className="panel-note">{t("Statistics below describe displayed samples, not every source reading.")}</p><div className="table-wrap"><table className="data-table"><thead><tr>{["Machine", "Module", "Metric", "Samples", "Latest", "Avg", "Min", "Max"].map(label => <th key={label}>{t(label)}</th>)}</tr></thead><tbody>{request.series.flatMap(item => request.metrics.filter(metric => metric.source === historySource(item.module)).map(metric => {
              const values = (results[item.key]?.rows || []).map(row => numeric(row[metric.key])).filter(value => value !== null);
              return <tr key={`${item.key}:${metric.id}`}><td>{machineName(item.device)}</td><td>{item.module.module_name}</td><td>{t(metric.label)}{metric.unit ? ` (${metric.unit})` : ""}</td><td>{values.length.toLocaleString()}</td><td>{formatNumber(values.at(-1))}</td><td>{formatNumber(values.length ? values.reduce((sum, value) => sum + value, 0) / values.length : null)}</td><td>{formatNumber(values.length ? Math.min(...values) : null)}</td><td>{formatNumber(values.length ? Math.max(...values) : null)}</td></tr>;
            }))}</tbody></table></div></article>
          </>}
        </> : <article className="panel"><Empty>{t("Select a machine, module, signals and date/time, then load charts.")}</Empty></article>}
      </section>
    </div>
  </>;
}

export function HistoricalDatabase({ devices, api, notify, t, downloadRows }) {
  const [deviceId, setDeviceId] = useState("");
  const [moduleId, setModuleId] = useState("");
  const [window, setWindow] = useState(initialWindow);
  const [dataset, setDataset] = useState("readings");
  const [limit, setLimit] = useState(100);
  const [result, setResult] = useState(null);
  const [request, setRequest] = useState(null);
  const [loading, setLoading] = useState(false);
  const controller = useRef(null);
  const device = devices.find(item => String(item.id) === deviceId);
  const module = machineModules(device).find(item => String(item.id) === moduleId);
  const source = historySource(module);
  const invalidate = () => { controller.current?.abort(); setLoading(false); setResult(null); setRequest(null); };
  useEffect(() => () => controller.current?.abort(), []);
  const load = async (offset = 0, snapshot = { device, module, window: { ...window }, limit }) => {
    if (!snapshot.device || !snapshot.module || windowError(snapshot.window)) return;
    controller.current?.abort(); const abort = new AbortController(); controller.current = abort;
    setLoading(true); setRequest(snapshot);
    try {
      const params = new URLSearchParams({ ...windowParams(snapshot.window), module_id: String(snapshot.module.id), limit: String(snapshot.limit), offset: String(offset) });
      const data = await api(`/api/devices/${snapshot.device.id}/history-page?${params}`, { signal: abort.signal });
      if (!Array.isArray(data?.rows)) throw new Error("Invalid telemetry response");
      if (!abort.signal.aborted) setResult(data);
    } catch (error) {
      if (!abort.signal.aborted) notify("error", "Database", error.message);
    } finally { if (!abort.signal.aborted) setLoading(false); }
  };
  const metrics = HISTORY_METRICS[source] || [];
  const rows = dataset === "metrics" ? (result?.rows || []).flatMap(row => metrics.filter(metric => numeric(row[metric.key]) !== null).map(metric => ({ ...row, metric_key: metric.label, metric_value: row[metric.key], unit: metric.unit }))) : result?.rows || [];
  const columns = [["recorded_at", "Recorded"], ["machine_code", "Machine"], ["module_name", "Module"], ...(dataset === "metrics" ? [["metric_key", "Metric"], ["metric_value", "Value"], ["unit", "Unit"]] : [...metrics.map(metric => [metric.key, `${t(metric.label)}${metric.unit ? ` (${metric.unit})` : ""}`]), ...(source === "compressor" ? [["operating_status", "Status"], ["set_valve_status", "SV"]] : [])])];
  const filename = `${request?.device.machine_code || "history"}-${request?.module.module_code || "module"}-${dataset}-page-${result?.offset || 0}`;
  return <>
    <div className="section-title"><div><span className="eyebrow">{t("Data")}</span><h2>{t("Telemetry Records")}</h2></div><div className="database-actions"><button className="ghost-btn" disabled={loading || !rows.length} onClick={() => downloadRows(rows, "csv", filename)}>{t("Export page")} · CSV</button><button className="ghost-btn" disabled={loading || !rows.length} onClick={() => downloadRows(rows, "json", filename)}>{t("Export page")} · JSON</button></div></div>
    <article className="panel history-database-controls">
      <div className="panel-head"><h3>{t("Select historical data")}</h3></div>
      <MachineModuleControls devices={devices} deviceId={deviceId} moduleId={moduleId} t={t} onMachine={id => { invalidate(); setDeviceId(id); setModuleId(""); }} onModule={id => { invalidate(); setModuleId(id); }} />
      <TimeControls value={window} t={t} onChange={value => { invalidate(); setWindow(value); }} />
      <div className="history-database-options"><label>{t("Dataset")}<select value={dataset} onChange={event => { setDataset(event.target.value); if (event.target.value === "metrics" && limit > 100) { invalidate(); setLimit(100); } }}><option value="readings">{t("Sensor readings")}</option><option value="metrics">{t("Dynamic metrics")}</option></select></label><label>{t("Readings per page")}<select value={limit} onChange={event => { invalidate(); setLimit(Number(event.target.value)); }}>{(dataset === "metrics" ? [100] : [100, 250, 500, 1000]).map(size => <option key={size}>{size}</option>)}</select></label><button className="primary-btn" disabled={loading || !module || !!windowError(window)} onClick={() => load()}>{t(loading ? "Loading" : "Load data")}</button></div>
    </article>
    <article className="panel database-table-panel" aria-busy={loading}><div className="panel-head"><div><h3>{t("Data Preview")}</h3><p className="panel-note">{result ? `${result.total.toLocaleString()} ${t("source readings")} · ${t("Latest first")}` : t("Select a machine first.")}</p></div></div>
      {result?.rows.length ? <><div className="table-wrap history-data-scroll"><table className="data-table database-table"><thead><tr>{columns.map(([key, label]) => <th key={key}>{t(label)}</th>)}</tr></thead><tbody>{rows.map(row => <tr key={`${row.id}:${row.metric_key || ""}`}>
        {columns.map(([key]) => <td key={key}>{key === "recorded_at" ? formatTime(row[key]) : row[key] == null ? "—" : typeof row[key] === "number" ? formatNumber(row[key]) : String(row[key])}</td>)}
      </tr>)}</tbody></table></div><div className="pagination-actions"><button className="ghost-btn" disabled={loading || result.offset === 0} onClick={() => load(Math.max(0, result.offset - request.limit), request)}>{t("Previous")}</button><span>{result.offset + 1}–{Math.min(result.offset + result.rows.length, result.total)} / {result.total.toLocaleString()} {t("source readings")}</span><button className="ghost-btn" disabled={loading || result.offset + result.limit >= result.total} onClick={() => load(result.offset + request.limit, request)}>{t("Next")}</button></div></> : <Empty>{t(loading ? "Loading records" : result ? "No telemetry in the selected range" : "Select a machine, module and date/time, then load data.")}</Empty>}
    </article>
  </>;
}
