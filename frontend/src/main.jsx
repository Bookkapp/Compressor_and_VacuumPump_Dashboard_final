import { PRESSURE_COLORS, bindChartCoordinates, pressureAxis, controlStateOption } from "./chart-behavior.mjs";
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { LANGUAGE_KEY, translate } from "./i18n";
import { COMPRESSOR_SIGNALS, COMPRESSOR_HISTORY_SIGNALS, VACUUM_SIGNALS, historyRowsEqual, historyCorrelation, historyRelationship } from "./detail-telemetry.mjs";
import { HistoricalCharts, HistoricalDatabase } from "./HistoryPages";
import { createRoot } from "react-dom/client";
import { createPortal } from "react-dom";
import * as echarts from "echarts/core";
import { BarChart, HeatmapChart, LineChart, PieChart, ScatterChart } from "echarts/charts";
import { DataZoomComponent, GridComponent, LegendComponent, MarkAreaComponent, TooltipComponent, VisualMapComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import {
  Activity,
  AlertTriangle,
  ArrowLeft,
  BarChart3,
  Bell,
  Check,
  ChevronRight,
  Database,
  Download,
  Edit3,
  Eye,
  EyeOff,
  LayoutDashboard,
  Languages,
  LogOut,
  MapPin,
  Moon,
  Plus,
  RefreshCcw,
  Save,
  Search,
  Server,
  Settings,
  ShieldCheck,
  Sun,
  Table2,
  Thermometer,
  Trash2,
  Wifi,
  WifiOff,
  Wrench,
  Zap,
  X,
} from "lucide-react";
import "./styles.css";

echarts.use([BarChart, HeatmapChart, LineChart, PieChart, ScatterChart, DataZoomComponent, GridComponent, LegendComponent, MarkAreaComponent, TooltipComponent, VisualMapComponent, CanvasRenderer]);

const TOKEN_KEY = "adi_token";
const THEME_KEY = "adi_theme";
const TranslationContext = React.createContext((text) => text);
const useT = () => React.useContext(TranslationContext);
const LOGO = "/assets/adi-logo.png?v=20260703-logo";
const CHART_AXIS = "#98a6af";
const CHART_GRID = "#293034";
const CHART_TEXT = "#e9edef";
const COLOR_GOOD = "#42b883";
const COLOR_WARN = "#e3a32b";
const COLOR_DANGER = "#ed5a62";
const COLOR_TEAL = "#38c3c7";
const COLOR_BLUE = "#4f96d1";
const COLOR_OFFLINE = "#6f7b83";
const PRIMARY_SENSOR_KEYS = ["health_score", "temperature_c", "pressure_kpa", "current_a", "vibration"];
const ACCEL_SNAPSHOT_KEYS = ["accel_x", "accel_y", "accel_z"];

const HANDLER_FILTER_OPTIONS = [
  { key: "ALL", label: "All" },
  { key: "GOOD", label: "Good", statuses: ["NORMAL", "GOOD", "MONITORING"] },
  { key: "WARNING", label: "Warning", statuses: ["WARNING", "WATCH"] },
  { key: "REPAIR_NOW", label: "Repair Now", statuses: ["MAINTENANCE_REQUIRED"] },
  { key: "REPAIRING", label: "Repairing", statuses: ["UNDER_MAINTENANCE"] },
  { key: "OFFLINE", label: "Offline", statuses: ["OFFLINE"] },
  { key: "NOT_EVALUATED", label: "Pending", statuses: ["NOT_EVALUATED", "AWAITING_ML_SCORE"] },
];
const HANDLER_FILTER_BY_KEY = Object.fromEntries(HANDLER_FILTER_OPTIONS.map((item) => [item.key, item]));
const MODULE_STATUS_OPTIONS = [
  ["NORMAL", "Good"],
  ["WARNING", "Warning"],
  ["MAINTENANCE_REQUIRED", "Repair Now"],
  ["UNDER_MAINTENANCE", "Repairing"],
  ["OFFLINE", "Offline"],
];
const VALID_VIEWS = ["overview", "handlers", "alerts", "maintenance", "database", "history", "logs", "compare", "admin"];
const EMPTY_HISTORY = Object.freeze([]);

function cls(...items) {
  return items.filter(Boolean).join(" ");
}

function n(value, digits = 1) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed.toFixed(digits) : "--";
}

function ago(seconds) {
  const thai = document.documentElement.lang === "th";
  if (seconds === null || seconds === undefined) return thai ? "ไม่เคย" : "never";
  if (seconds < 5) return thai ? "เมื่อสักครู่" : "just now";
  if (seconds < 60) return thai ? `${seconds} วินาทีที่แล้ว` : `${seconds}s ago`;
  if (seconds < 3600) return thai ? `${Math.floor(seconds / 60)} นาทีที่แล้ว` : `${Math.floor(seconds / 60)}m ago`;
  return thai ? `${Math.floor(seconds / 3600)} ชั่วโมงที่แล้ว` : `${Math.floor(seconds / 3600)}h ago`;
}

function dateText(value) {
  if (!value) return "--";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? "--" : d.toLocaleString(document.documentElement.lang === "th" ? "th-TH-u-ca-gregory" : "en-GB");
}

function conditionLabel(value) {
  if (value === "NOT_EVALUATED") return "PENDING";
  if (value === "UNREGISTERED") return "UNREGISTERED";
  if (value === "AWAITING_ML_SCORE") return "AWAITING ML SCORE";
  if (value === "MAINTENANCE_REQUIRED") return "REPAIR NOW";
  if (value === "UNDER_MAINTENANCE") return "REPAIRING";
  if (value === "WATCH") return "WARNING";
  if (value === "MONITORING") return "GOOD";
  if (value === "NORMAL") return "GOOD";
  return value || "OFFLINE";
}

function moduleHasTelemetry(module) {
  return Boolean(module) && PRIMARY_SENSOR_KEYS.some((key) => module[key] !== null && module[key] !== undefined);
}

function moduleSource(module) {
  if (module?.telemetry_source) return module.telemetry_source;
  return String(module?.module_code || "").startsWith("compressor-") ? "compressor" : "vacuum";
}

function isActiveSourceModule(module) {
  if (moduleSource(module) !== "compressor" || module?.source_status === null || module?.source_status === undefined) return true;
  return ["on", "run", "running", "active", "1", "true"].includes(String(module.source_status).trim().toLowerCase());
}

function activeModules(device) {
  return (device?.modules || []).filter(isActiveSourceModule);
}

function groupedModules(device, activeOnly = false) {
  const groups = new Map();
  (activeOnly ? activeModules(device) : (device?.modules || [])).forEach((module) => {
    const source = moduleSource(module);
    if (!groups.has(source)) groups.set(source, []);
    groups.get(source).push(module);
  });
  return [...groups.entries()].map(([source, modules]) => ({
    source,
    label: source === "compressor" ? "Compressor" : "Vacuum Pump",
    modules,
  }));
}

function accelSnapshotValue(module, key) {
  const raw = module?.metrics?.[key] ?? module?.[key];
  if (raw === null || raw === undefined || raw === "" || !Number.isFinite(Number(raw))) return null;
  return `${n(raw, 3)} ${module?.metric_units?.[key] || "g"}`;
}

function sourceMetricLabel(key) {
  return {
    hp_1st: "HP1 · High Pressure COM1", lp_1st: "LP1 · Low Pressure COM1", hp_2nd: "HP2 · High Pressure COM2", lp_2nd: "LP2 · Low Pressure COM2",
    temperature_hi: "Temp Hi", temperature_lo: "Temp Lo",
    current_amp: "Current", accel_x: "Accel X", accel_y: "Accel Y", accel_z: "Accel Z",
  }[key] || key.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function isUnregisteredDevice(device) {
  const modules = device?.modules || [];
  return !modules.length || !device?.last_seen || !modules.some(moduleHasTelemetry);
}

function displayDeviceStatus(device) {
  return isUnregisteredDevice(device) ? "UNREGISTERED" : device?.connection_state === "OFFLINE" ? "OFFLINE" : device?.status;
}

function displayModuleStatus(module) {
  return moduleHasTelemetry(module) ? module.status : "UNREGISTERED";
}

function machineTitle(device) {
  const raw = String(device?.machine_code || device?.display_name || device?.device_uid || "").trim();
  const withoutPrefix = raw.replace(/^(?:Handler|Vacuum Pump|Compressor)\s+/i, "");
  const match = withoutPrefix.match(/^(?:HT9046MX[-_]?|MX[-_]?|VP[-_]?)?0*(\d+)$/i);
  return match && match[1] ? `HT9046MX-${match[1].padStart(3, "0")}` : withoutPrefix || "HT9046MX";
}

function handlerMatchesFilter(device, filterKey) {
  const option = HANDLER_FILTER_BY_KEY[filterKey] || HANDLER_FILTER_BY_KEY.ALL;
  if (option.key === "ALL") return true;
  const unregistered = isUnregisteredDevice(device);
  if (unregistered) return false;
  const statusMatch = option.statuses?.includes(device.status);
  const connectionMatch = option.connectionStates?.includes(device.connection_state);
  return Boolean(statusMatch || connectionMatch);
}

function handlerFilterLabel(filterKey) {
  return HANDLER_FILTER_BY_KEY[filterKey]?.label || "All";
}

async function parseResponse(res) {
  const text = await res.text();
  try {
    return text ? JSON.parse(text) : null;
  } catch {
    return text;
  }
}

function chartOptionForTheme(option, themeMode) {
  if (!option) return option;
  const light = themeMode === "light";
  const axisColor = light ? "#667680" : CHART_AXIS;
  const gridColor = light ? "#dce3e8" : CHART_GRID;
  const textColor = light ? "#1c2931" : CHART_TEXT;
  const tooltipBackground = light ? "#ffffff" : "#101518";
  const tooltipBorder = light ? "#ccd6dd" : "#30383d";

  const patchAxis = (axis) => {
    if (!axis) return axis;
    if (Array.isArray(axis)) return axis.map(patchAxis);
    return {
      ...axis,
      axisLabel: axis.axisLabel ? { ...axis.axisLabel, color: axisColor } : axis.axisLabel,
      nameTextStyle: axis.nameTextStyle ? { ...axis.nameTextStyle, color: axisColor } : axis.nameTextStyle,
      axisLine: axis.axisLine
        ? { ...axis.axisLine, lineStyle: { ...axis.axisLine.lineStyle, color: gridColor } }
        : axis.axisLine,
      splitLine: axis.splitLine
        ? { ...axis.splitLine, lineStyle: { ...axis.splitLine.lineStyle, color: gridColor } }
        : axis.splitLine,
    };
  };

  return {
    ...option,
    textStyle: { ...option.textStyle, color: textColor },
    tooltip: option.tooltip
      ? {
          ...option.tooltip,
          backgroundColor: tooltipBackground,
          borderColor: tooltipBorder,
          textStyle: { ...option.tooltip.textStyle, color: textColor },
          extraCssText: `box-shadow: 0 10px 28px ${light ? "rgba(28, 41, 49, 0.14)" : "rgba(0, 0, 0, 0.34)"}; border-radius: 6px;`,
        }
      : option.tooltip,
    legend: option.legend
      ? { ...option.legend, textStyle: { ...option.legend.textStyle, color: axisColor } }
      : option.legend,
    xAxis: patchAxis(option.xAxis),
    yAxis: patchAxis(option.yAxis),
    series: Array.isArray(option.series)
      ? option.series.map((series) => ({
          ...series,
          label: series.label ? { ...series.label, color: textColor } : series.label,
        }))
      : option.series,
  };
}

function EChart({ option, className = "chart" }) {
  const ref = useRef(null);
  const chartRef = useRef(null);
  const [themeMode, setThemeMode] = useState(() => document.documentElement.dataset.theme || "dark");

  const latest = useRef({ option, themeMode });
  latest.current = { option, themeMode };
  const applied = useRef(null);
  useEffect(() => {
    const node = ref.current;
    if (!node) return undefined;
    const create = () => {
      if (chartRef.current) return;
      const started = performance.now();
      const chart = echarts.init(node, null, { renderer: "canvas" });
      chartRef.current = chart;
      node._unbindChartCoordinates = bindChartCoordinates(node, chart);
      chart.on("finished", () => { if (!node.dataset.renderMs) node.dataset.renderMs = String(Math.round(performance.now() - started)); });
      chart.setOption(chartOptionForTheme(latest.current.option, latest.current.themeMode), true);
      node.dataset.optionUpdates = "1";
      applied.current = latest.current;
    };
    // Prepare charts near the viewport, avoiding offscreen canvas work per tab.
    const observer = new IntersectionObserver(entries => {
      if (entries.some(entry => entry.isIntersecting)) { create(); observer.disconnect(); }
    }, { rootMargin: "150px" });
    observer.observe(node);
    const resize = () => chartRef.current?.resize();
    window.addEventListener("resize", resize);
    const sizeObserver = new ResizeObserver(resize);
    sizeObserver.observe(node);
    return () => {
      observer.disconnect(); sizeObserver.disconnect(); node._unbindChartCoordinates?.(); window.removeEventListener("resize", resize);
      chartRef.current?.dispose(); chartRef.current = null;
    };
  }, []);

  useEffect(() => {
    const handleThemeChange = (event) => setThemeMode(event.detail);
    window.addEventListener("adi-theme-change", handleThemeChange);
    return () => window.removeEventListener("adi-theme-change", handleThemeChange);
  }, []);

  useEffect(() => {
    if (chartRef.current && option && (applied.current?.option !== option || applied.current?.themeMode !== themeMode)) {
      applied.current = { option, themeMode };
      chartRef.current.setOption(chartOptionForTheme(option, themeMode), true);
      ref.current.dataset.optionUpdates = String(Number(ref.current.dataset.optionUpdates || 0) + 1);
      setTimeout(() => chartRef.current?.resize(), 40);
    }
  }, [option, themeMode]);

  return <div ref={ref} className={className} />;
}

function LoadingButton({ busy, children, busyText = "Processing", icon: Icon, className = "primary-btn", ...props }) {
  return (
    <button className={className} {...props} disabled={busy || props.disabled}>
      {busy ? <span className="spinner" /> : Icon ? <Icon size={16} /> : null}
      <span>{busy ? busyText : children}</span>
    </button>
  );
}

function ToastStack({ toasts, dismiss }) {
  return (
    <div className="toast-stack">
      {toasts.map((toast) => (
        <div key={toast.id} className={cls("toast", toast.type)}>
          <strong>{toast.title}</strong>
          <span>{toast.message}</span>
          <button onClick={() => dismiss(toast.id)} aria-label="Dismiss">
            <X size={14} />
          </button>
        </div>
      ))}
    </div>
  );
}

function StatusBadge({ value }) {
  const t = useT();
  return <span className={cls("state-badge", value)}>{t(conditionLabel(value))}</span>;
}

function ConnectionBadge({ state, seconds }) {
  const t = useT();
  const Icon = state === "ONLINE" ? Wifi : WifiOff;
  return (
    <span className={cls("connection-badge", state)}>
      <Icon size={14} />
      <span>{t(connectionLabel(state))}</span>
      <small>{state === "UNREGISTERED" ? t("not linked") : ago(seconds)}</small>
    </span>
  );
}

function connectionLabel(state) {
  if (state === "UNREGISTERED") return "Unregistered";
  if (state === "ONLINE") return "Online";
  if (state === "STALE") return "Stale";
  if (state === "OFFLINE") return "Offline";
  return "No Signal";
}

function Empty({ children }) {
  return <div className="empty-state">{children}</div>;
}

function Skeleton({ width = "100%", height = 16, count = 1, className = "" }) {
  return (
    <div className={cls("skeleton-group", className)}>
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="skeleton-bar" style={{ width, height }} />
      ))}
    </div>
  );
}

function sinceFromRange(range) {
  if (!range || range.toLowerCase() === "all") return "";
  const hours = { "1h": 1, "6h": 6, "24h": 24, "7d": 168 }[range] || 6;
  return new Date(Date.now() - hours * 3600000).toISOString();
}

function formNumber(form, name) {
  const value = String(form.get(name) ?? "").trim();
  return value === "" ? null : Number(value);
}

function formatCell(value) {
  if (value === null || value === undefined || value === "") return "-";
  if (typeof value === "number") return Number.isInteger(value) ? value.toLocaleString() : n(value, 3);
  return String(value);
}

function csvValue(value) {
  if (value === null || value === undefined) return "";
  const text = typeof value === "object" ? JSON.stringify(value) : String(value);
  return /[",\r\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function rowsToCsv(rows) {
  if (!rows.length) return "";
  const columns = [...rows.reduce((set, row) => {
    Object.keys(row || {}).forEach((key) => set.add(key));
    return set;
  }, new Set())];
  return [
    columns.join(","),
    ...rows.map((row) => columns.map((column) => csvValue(row[column])).join(",")),
  ].join("\n");
}

function downloadRows(rows, format, filenameBase) {
  if (!rows.length) return;
  const isJson = format === "json";
  const content = isJson ? JSON.stringify(rows, null, 2) : rowsToCsv(rows);
  const blob = new Blob([content], { type: isJson ? "application/json" : "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${filenameBase}.${isJson ? "json" : "csv"}`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function App() {
  const [language, setLanguageState] = useState(() => localStorage.getItem(LANGUAGE_KEY) === "th" ? "th" : "en");
  const t = useCallback((text) => translate(language, text), [language]);
  const setLanguage = useCallback((next) => {
    const code = next === "th" ? "th" : "en";
    localStorage.setItem(LANGUAGE_KEY, code);
    document.documentElement.lang = code;
    setLanguageState(code);
  }, []);
  useEffect(() => { document.documentElement.lang = language; }, [language]);
  const [themeMode, setThemeModeState] = useState(() => {
    const storedTheme = localStorage.getItem(THEME_KEY) === "light" ? "light" : "dark";
    document.documentElement.dataset.theme = storedTheme;
    return storedTheme;
  });
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY));
  const [user, setUser] = useState(null);

  const [view, setView] = useState(() => {
    const hash = window.location.hash.replace("#", "");
    return VALID_VIEWS.includes(hash) ? hash : "overview";
  });
  const [dbStatus, setDbStatus] = useState(null);
  const [summary, setSummary] = useState(null);
  const [devices, setDevices] = useState([]);
  const [users, setUsers] = useState([]);
  const [workOrders, setWorkOrders] = useState([]);
  const [logs, setLogs] = useState([]);
  const [alerts, setAlerts] = useState([]);
  const [handlerFilter, setHandlerFilter] = useState("ALL");
  const [searchQuery, setSearchQuery] = useState("");
  const [loginForm, setLoginForm] = useState({ username: "ADIadmin", password: "" });
  const [busy, setBusy] = useState({});
  const [toasts, setToasts] = useState([]);
  const [detailDeviceId, setDetailDeviceId] = useState(null);
  const [detailModuleId, setDetailModuleId] = useState(null);
  const [history, setHistory] = useState([]);
  const [detailTelemetry, setDetailTelemetry] = useState({ key: null, loading: true, error: "" });
  const [detailTimeRange, setDetailTimeRange] = useState("All");
  const [editingDeviceId, setEditingDeviceId] = useState(null);
  const [deviceDraft, setDeviceDraft] = useState({});
  const [hiddenIds, setHiddenIds] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem("pm_hidden_machines") || "[]");
    } catch {
      return [];
    }
  });
  const refreshTimer = useRef(null);
  const refreshSequence = useRef(0);

  const toggleHideDevice = useCallback((device) => {
    const id = device?.id;
    if (!id) return;
    setHiddenIds((prev) => {
      const isCurrentlyHidden = prev.includes(id);
      const next = isCurrentlyHidden ? prev.filter((item) => item !== id) : [...prev, id];
      try {
        localStorage.setItem("pm_hidden_machines", JSON.stringify(next));
      } catch {}
      return next;
    });
  }, []);

  const setThemeMode = useCallback((nextTheme) => {
    const normalizedTheme = nextTheme === "light" ? "light" : "dark";
    document.documentElement.dataset.theme = normalizedTheme;
    localStorage.setItem(THEME_KEY, normalizedTheme);
    setThemeModeState(normalizedTheme);
    window.dispatchEvent(new CustomEvent("adi-theme-change", { detail: normalizedTheme }));
  }, []);

  const authHeaders = useMemo(() => (token ? { Authorization: `Bearer ${token}` } : {}), [token]);

  const notify = useCallback((type, title, message) => {
    const id = `${Date.now()}-${Math.random()}`;
    setToasts((items) => [...items, { id, type, title, message }]);
    setTimeout(() => {
      setToasts((items) => items.filter((item) => item.id !== id));
    }, 4200);
  }, []);

  const dismissToast = useCallback((id) => {
    setToasts((items) => items.filter((item) => item.id !== id));
  }, []);

  const api = useCallback(async (path, options = {}) => {
    const res = await fetch(path, {
      method: options.method || "GET",
      headers: {
        ...(options.auth === false ? {} : authHeaders),
        ...(options.body ? { "Content-Type": "application/json" } : {}),
      },
      cache: "no-store",
      signal: options.signal,
      body: options.body ? JSON.stringify(options.body) : undefined,
    });
    const data = await parseResponse(res);
    if (!res.ok) {
      if (res.status === 401) {
        if (localStorage.getItem(TOKEN_KEY) === token) localStorage.removeItem(TOKEN_KEY);
        setToken(null);
        setUser(null);
      }
      throw new Error(data?.detail || data?.error || data || res.statusText);
    }
    return data;
  }, [authHeaders]);

  const runBusy = useCallback(async (key, task, successMessage) => {
    setBusy((b) => ({ ...b, [key]: true }));
    try {
      const result = await task();
      if (successMessage) notify("success", "Success", successMessage);
      return result;
    } catch (error) {
      notify("error", "Failed", error.message || "Operation failed");
      throw error;
    } finally {
      setBusy((b) => ({ ...b, [key]: false }));
    }
  }, [notify]);

  const refreshStatus = useCallback(async () => {
    const status = await api("/api/db/status", { auth: false });
    setDbStatus(status);
  }, [api]);

  const refreshAll = useCallback(async () => {
    if (!token) return;
    const sequence = ++refreshSequence.current;
    await refreshStatus();
    const requests = [
      api("/api/summary"),
      api("/api/devices"),
      api("/api/work-orders"),
      api("/api/maintenance-logs"),
      api("/api/alerts?limit=500"),
    ];
    if (user?.role === "admin") requests.push(api("/api/users"));
    const [nextSummary, nextDevices, nextWorkOrders, nextLogs, nextAlerts, nextUsers] = await Promise.all(requests);
    if (sequence !== refreshSequence.current) return;
    setSummary(nextSummary);
    setDevices(nextDevices || []);
    setWorkOrders(nextWorkOrders || []);
    setLogs(nextLogs || []);
    setAlerts(nextAlerts || []);
    if (nextUsers) setUsers(nextUsers || []);
  }, [api, refreshStatus, token, user?.role]);

  const scheduleRefresh = useCallback(() => {
    clearTimeout(refreshTimer.current);
    refreshTimer.current = setTimeout(() => {
      refreshAll().catch((error) => notify("error", "Refresh failed", error.message));
    }, 300);
  }, [notify, refreshAll]);

  useEffect(() => {
    if (!token) return;
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    let closedByCleanup = false;
    let reconnectTimer;
    let ws;

    const connect = () => {
      ws = new WebSocket(`${protocol}://${window.location.host}/ws`, ["adi-v1", token]);
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.event === "state_update") {
            if (msg.summary) setSummary(msg.summary);
            if (msg.devices) setDevices(msg.devices);
            if (msg.alerts) setAlerts(msg.alerts);
          } else {
            scheduleRefresh();
          }
        } catch {
          scheduleRefresh();
        }
      };
      ws.onerror = () => ws.close();
      ws.onclose = () => {
        if (!closedByCleanup) reconnectTimer = window.setTimeout(connect, 2500);
      };
    };

    connect();

    return () => {
      closedByCleanup = true;
      window.clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, [scheduleRefresh, token]);

  useEffect(() => {
    if (!token) return;
    api("/api/auth/me")
      .then((me) => {
        setUser(me);
      })
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY);
        setToken(null);
        setUser(null);
      });
  }, [api, token]);

  // Refresh immediately when changing view or logging in
  useEffect(() => {
    if (!token || !user) return;
    refreshAll().catch(() => {});
  }, [refreshAll, token, user, view]);

  // WebSocket handles active live state; hidden tabs need no repeated full fetch.
  useEffect(() => {
    if (!token || !user) return;
    const interval = setInterval(() => {
      if (document.visibilityState === "visible") refreshAll().catch(() => {});
    }, 15000);
    const onVisible = () => {
      if (document.visibilityState === "visible") refreshAll().catch(() => {});
    };
    document.addEventListener("visibilitychange", onVisible);
    return () => { clearInterval(interval); document.removeEventListener("visibilitychange", onVisible); };
  }, [refreshAll, token, user]);

  const detailDevice = useMemo(() => devices.find((d) => d.id === detailDeviceId), [detailDeviceId, devices]);
  const detailModule = useMemo(() => {
    if (!detailDevice) return null;
    const modules = detailDevice.modules || [];
    return modules.find((m) => m.id === detailModuleId) || modules[0] || null;
  }, [detailDevice, detailModuleId]);

  const stableDetailDeviceId = detailDevice?.id;
  const stableDetailModuleId = detailModule?.id;
  const stableDetailSource = detailModule ? moduleSource(detailModule) : null;

  // Poll the open chart only; skip hidden tabs and overlapping history queries.
  useEffect(() => {
    if (!stableDetailDeviceId || !stableDetailModuleId || !token) return;
    let active = true;
    const abort = new AbortController();
    const key = `${stableDetailDeviceId}:${stableDetailModuleId}:${detailTimeRange}`;
    setHistory([]);
    setDetailTelemetry({ key, loading: true, error: "" });
    let previous = null;
    let firstLoad = true;
    let inFlight = false;
    const loadDetailTelemetry = async () => {
      if (!active || inFlight || document.visibilityState !== "visible") return;
      inFlight = true;
      const since = sinceFromRange(detailTimeRange);
      const sinceQuery = since ? `&since=${encodeURIComponent(since)}` : "";
      const signals = (stableDetailSource === "compressor" ? COMPRESSOR_HISTORY_SIGNALS : VACUUM_SIGNALS).join(",");
      try {
        const nextHistory = await api(`/api/devices/${stableDetailDeviceId}/history?module_id=${stableDetailModuleId}&limit=2000&signals=${signals}${sinceQuery}`, { signal: abort.signal });
        if (!active) return;
        // Keep cached chart options and zoom when a poll returns identical data.
        if (!historyRowsEqual(previous, nextHistory)) { previous = nextHistory; setHistory(nextHistory); }
        const initial = firstLoad;
        setDetailTelemetry(current => initial || current.error ? { key, loading: false, error: "" } : current);
        firstLoad = false;
      } catch (error) {
        if (active && error.name !== "AbortError") setDetailTelemetry(current => ({ ...current, loading: false, error: error.message }));
      }
      finally { inFlight = false; }
    };
    loadDetailTelemetry();
    const interval = setInterval(loadDetailTelemetry, 4000);
    document.addEventListener("visibilitychange", loadDetailTelemetry);
    return () => { active = false; abort.abort(); clearInterval(interval); document.removeEventListener("visibilitychange", loadDetailTelemetry); };
  }, [api, stableDetailDeviceId, stableDetailModuleId, stableDetailSource, detailTimeRange, token]);

  const login = async (event) => {
    event.preventDefault();
    await runBusy("login", async () => {
      const data = await api("/api/auth/login", { method: "POST", auth: false, body: loginForm });
      setToken(data.token);
      setUser(data.user);
      localStorage.setItem(TOKEN_KEY, data.token);
      notify("success", "Logged in", `Welcome ${data.user.username}`);
    });
  };

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY);
    setToken(null);
    setUser(null);
    setView("overview");
  };

  const safeSetView = (nextView) => {
    if (editingDeviceId && !window.confirm("You have unsaved edits. Leave without saving?")) {
      return false;
    }
    setEditingDeviceId(null);
    setDeviceDraft({});
    setDetailDeviceId(null);
    setDetailModuleId(null);
    setHistory([]);
    setView(nextView);
    window.location.hash = nextView;
    return true;
  };

  useEffect(() => {
    const onHashChange = () => {
      const hash = window.location.hash.replace("#", "");
      if (VALID_VIEWS.includes(hash) && hash !== view) setView(hash);
    };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, [view]);

  useEffect(() => {
    if (!token || !user) return;
    const onKeyDown = (e) => {
      const tag = document.activeElement?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      const shortcuts = { "1": "overview", "2": "handlers", "3": "alerts", "4": "maintenance", "5": "database", "6": "compare" };
      if (user.role === "admin") shortcuts["7"] = "admin";
      if (shortcuts[e.key]) {
        e.preventDefault();
        setEditingDeviceId(null);
        setDeviceDraft({});
        setDetailDeviceId(null);
        setDetailModuleId(null);
        setHistory([]);
        setView(shortcuts[e.key]);
        window.location.hash = shortcuts[e.key];
      } else if (e.key === "r" || e.key === "R") {
        e.preventDefault();
        refreshAll().catch(() => {});
      } else if (e.key === "Escape" && detailDeviceId) {
        setDetailDeviceId(null);
      } else if (e.key === "/") {
        e.preventDefault();
        document.querySelector(".search-box input")?.focus();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [token, user, detailDeviceId, refreshAll]);

  const openHandlersForFilter = (filterKey = "ALL") => {
    if (safeSetView("handlers")) {
      setHandlerFilter(filterKey);
    }
  };

  const openAlerts = () => {
    safeSetView("alerts");
  };

  const openDetail = (device, selectedModule = null) => {
    const targetModule = selectedModule || worstModule(device) || device.modules?.[0];
    setDetailDeviceId(device.id);
    setDetailModuleId(targetModule?.id || null);
  };

  const openAlertDetail = (alert) => {
    const device = devices.find((item) => item.id === alert.device_id);
    if (!device) {
      notify("error", "Alert detail", "Device is no longer available");
      return;
    }
    const hasModule = (device.modules || []).some((module) => module.id === alert.module_id);
    const nextModuleId = hasModule ? alert.module_id : device.modules?.[0]?.id;
    if (!nextModuleId) {
      notify("error", "Alert detail", "No module registered for this handler");
      return;
    }
    setDetailDeviceId(device.id);
    setDetailModuleId(nextModuleId);
  };

  const submitDevice = (event) => {
    event.preventDefault();
    const formEl = event.currentTarget;
    const form = new FormData(formEl);
    runBusy("device:create", async () => {
      await api("/api/devices", {
        method: "POST",
        body: {
          device_uid: form.get("device_uid"),
          machine_code: form.get("machine_code"),
          display_name: form.get("display_name") || form.get("machine_code"),
          location: form.get("location"),
        },
      });
      formEl.reset();
      await refreshAll();
    }, "Device saved");
  };

  const submitModule = (event) => {
    event.preventDefault();
    const formEl = event.currentTarget;
    const form = new FormData(formEl);
    runBusy("module:create", async () => {
      await api(`/api/devices/${form.get("device_id")}/modules`, {
        method: "POST",
        body: {
          module_name: form.get("module_name"),
          module_code: form.get("module_code") || form.get("module_name"),
        },
      });
      formEl.reset();
      await refreshAll();
    }, "Module added");
  };

  const submitWorkOrder = (event) => {
    event.preventDefault();
    const formEl = event.currentTarget;
    const form = new FormData(formEl);
    runBusy("work:create", async () => {
      await api("/api/work-orders", {
        method: "POST",
        body: {
          device_id: Number(form.get("device_id")),
          module_id: Number(form.get("module_id")) || null,
          assigned_to: Number(form.get("assigned_to")) || null,
          priority: form.get("priority"),
          title: form.get("title"),
          description: form.get("description"),
          event_started_at: form.get("event_started_at") || null,
          event_ended_at: form.get("event_ended_at") || null,
          event_timezone: "Asia/Bangkok",
          event_time_precision: form.get("event_time_precision") || "UNKNOWN",
        },
      });
      formEl.reset();
      await refreshAll();
    }, "Work order assigned");
  };

  const submitThreshold = (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const moduleId = Number(form.get("module_id"));
    if (!moduleId) return;
    const thresholds = {
      enabled: form.has("advanced_enabled"),
      temperature_c: {
        warning: formNumber(form, "temperature_warning"),
        critical: formNumber(form, "temperature_critical"),
      },
      current_a: {
        warning: formNumber(form, "current_warning"),
        critical: formNumber(form, "current_critical"),
      },
      vibration: {
        warning: formNumber(form, "vibration_warning"),
        critical: formNumber(form, "vibration_critical"),
      },
    };
    runBusy("threshold:save", async () => {
      await api(`/api/modules/${moduleId}`, { method: "PATCH", body: { thresholds } });
      await refreshAll();
    }, "Threshold config saved");
  };

  const submitModuleStatus = (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const moduleId = Number(form.get("module_id"));
    if (!moduleId) return;
    runBusy("module:status", async () => {
      await api(`/api/modules/${moduleId}`, { method: "PATCH", body: { status: form.get("status") } });
      await refreshAll();
    }, "Module status updated");
  };

  const submitMaintenance = (event, parts = [], clearParts = () => {}) => {
    event.preventDefault();
    const formEl = event.currentTarget;
    const form = new FormData(formEl);
    runBusy("maintenance:create", async () => {
      await api("/api/maintenance-logs", {
        method: "POST",
        body: {
          device_id: Number(form.get("device_id")),
          module_id: Number(form.get("module_id")) || null,
          work_order_id: Number(form.get("work_order_id")) || null,
          technician_name: form.get("technician_name"),
          action_taken: form.get("action_taken"),
          parts,
          other_cost_baht: Number(form.get("other_cost_baht") || 0),
        },
      });
      formEl.reset();
      clearParts();
      await refreshAll();
    }, "Service log saved").catch(() => {});
  };

  const deleteMaintenanceLog = (logId) => {
    if (!window.confirm("Delete this maintenance log? This cannot be undone.")) return;
    runBusy(`maintenance:delete:${logId}`, async () => {
      await api(`/api/maintenance-logs/${logId}`, { method: "DELETE" });
      await refreshAll();
    }, "Maintenance log deleted").catch(() => {});
  };

  const updateMaintenanceLog = (logId, body) => runBusy(`maintenance:edit:${logId}`, async () => {
    await api(`/api/maintenance-logs/${logId}`, { method: "PATCH", body });
    await refreshAll();
  }, "Maintenance log updated");

  const deleteWorkOrder = (workId) => {
    if (!window.confirm(`Delete work order #${workId}? An audit record will be kept in MySQL.`)) return;
    runBusy(`work:delete:${workId}`, async () => {
      await api(`/api/work-orders/${workId}`, { method: "DELETE" });
      await refreshAll();
    }, "Work order deleted").catch(() => {});
  };

  const startEditDevice = (device) => {
    if (editingDeviceId && editingDeviceId !== device.id && !window.confirm("Discard current edits?")) {
      return;
    }
    setEditingDeviceId(device.id);
    setDeviceDraft({
      device_uid: device.device_uid || "",
      machine_code: device.machine_code || "",
      display_name: device.display_name || "",
      location: device.location || "",
    });
  };

  const saveDevice = (deviceId) => {
    runBusy(`device:save:${deviceId}`, async () => {
      await api(`/api/devices/${deviceId}`, { method: "PATCH", body: deviceDraft });
      setEditingDeviceId(null);
      setDeviceDraft({});
      await refreshAll();
    }, "Device updated");
  };

  const deleteDevice = (deviceId) => {
    if (!window.confirm("Delete this device and all related telemetry and logs?")) return;
    runBusy(`device:delete:${deviceId}`, async () => {
      await api(`/api/devices/${deviceId}`, { method: "DELETE" });
      await refreshAll();
    }, "Device deleted");
  };

  const updateWork = (workId, status) => {
    runBusy(`work:${workId}:${status}`, async () => {
      await api(`/api/work-orders/${workId}`, { method: "PATCH", body: { status } });
      await refreshAll();
    }, "Work order updated");
  };

  const clearAlerts = () => {
    if (!window.confirm("Clear all alert records from MySQL?")) return;
    runBusy("alerts:clear", async () => {
      await api("/api/alerts", { method: "DELETE" });
      setAlerts([]);
      await refreshAll();
    }, "Alert records cleared");
  };

  const acknowledgeAlert = (alertId) => {
    runBusy(`alert:ack:${alertId}`, async () => {
      const result = await api(`/api/alerts/${alertId}/acknowledge`, { method: "PATCH" });
      await refreshAll();
      return result;
    }).then((result) => {
      if (result) notify("success", "Alert acknowledged", result.work_order_id
        ? `Work order #${result.work_order_id} is ready in Maintenance. Alert suppressed for 7 days.`
        : "Alert suppressed for 7 days. No work order was created.");
    }).catch(() => {});
  };

  const selectedMaintDevice = devices[0];
  const selectedAdminDevice = devices[0];
  const alertBadgeCount = useMemo(() => {
    return alerts.filter((alert) => !alert.acknowledged).length;
  }, [alerts]);

  if (!token || !user) {
    return (
      <TranslationContext.Provider value={t}>
      <main className="login-shell">
        <ToastStack toasts={toasts} dismiss={dismissToast} />
        <form className="login-panel" onSubmit={login}>
          <Brand large />
          <label>
            {t("Username")}
            <input
              value={loginForm.username}
              onChange={(e) => setLoginForm({ ...loginForm, username: e.target.value })}
              autoComplete="username"
            />
          </label>
          <label>
            {t("Password")}
            <input
              value={loginForm.password}
              onChange={(e) => setLoginForm({ ...loginForm, password: e.target.value })}
              type="password"
              autoComplete="current-password"
              placeholder={t("Password")}
            />
          </label>
          <LoadingButton busy={busy.login} busyText="Logging in" icon={Check} type="submit">{t("Login")}</LoadingButton>
        </form>
      </main>
      </TranslationContext.Provider>
    );
  }

  return (
    <TranslationContext.Provider value={t}>
    <main className="app-shell">
      <ToastStack toasts={toasts} dismiss={dismissToast} />
      <header className="topbar">
        <Brand />
        <nav className="nav-tabs" aria-label="Primary navigation">
          <div className="nav-group">
            <span className="nav-group-label">{t("Operations")}</span>
            {[
              { key: "overview", label: "Overview", icon: LayoutDashboard },
              { key: "handlers", label: "Handlers", icon: Server },
              { key: "alerts", label: "Alerts", icon: Bell, badge: alertBadgeCount },
              { key: "maintenance", label: "Maintenance", icon: Wrench },
            ].map((tab) => (
              <button key={tab.key} className={view === tab.key ? "active" : ""} onClick={() => (tab.key === "alerts" ? openAlerts() : safeSetView(tab.key))}>
                {React.createElement(tab.icon, { size: 17 })}
                <span>{t(tab.label)}</span>
                {tab.badge > 0 && <span className="nav-badge">{tab.badge}</span>}
              </button>
            ))}
          </div>
          <div className="nav-group">
            <span className="nav-group-label">{t("Data")}</span>
            {[
              { key: "database", label: "Database", icon: Table2 },
              { key: "compare", label: "Analytics", icon: BarChart3 },
              { key: "history", label: "Historical Charts", icon: Activity },
              { key: "logs", label: "Logs", icon: Database },
            ].map((tab) => (
              <button key={tab.key} className={view === tab.key ? "active" : ""} onClick={() => safeSetView(tab.key)}>
                {React.createElement(tab.icon, { size: 17 })}
                <span>{t(tab.label)}</span>
              </button>
            ))}
          </div>
          {user.role === "admin" && (
            <div className="nav-group">
              <span className="nav-group-label">{t("System")}</span>
              <button className={view === "admin" ? "active" : ""} onClick={() => safeSetView("admin")}>
                <ShieldCheck size={17} />
                <span>{t("Admin")}</span>
              </button>
            </div>
          )}
        </nav>
        <div className="top-meta">
          <div className="user-badge">
            <span className="user-avatar">{user.username.slice(0, 2).toUpperCase()}</span>
            <span className="user-copy"><strong>{user.username}</strong><small>{user.role}</small></span>
          </div>
          <button className="ghost-btn" onClick={logout}><LogOut size={15} />{t("Logout")}</button>
        </div>
      </header>

      <section className="main-content">
        <CommandBar
          view={view}
          alertBadgeCount={alertBadgeCount}
          query={searchQuery}
          setQuery={setSearchQuery}
          openHandlers={() => openHandlersForFilter(handlerFilter)}
          openAlerts={openAlerts}
        />
        {view === "overview" && (
          <Overview
            summary={summary}
            devices={devices}
            workOrders={workOrders}
            alerts={alerts}
            api={api}
            metric={view}
            openAlerts={openAlerts}
            openHandlersForFilter={openHandlersForFilter}
            openDetail={openDetail}
            openMaintenance={() => safeSetView("maintenance")}
            refresh={() => runBusy("refresh", refreshAll, "Data refreshed")}
            refreshing={busy.refresh}
          />
        )}
        {view === "handlers" && (
          <Handlers
            devices={devices}
            filter={handlerFilter}
            setFilter={setHandlerFilter}
            searchQuery={searchQuery}
            openDetail={openDetail}
            hiddenIds={hiddenIds}
            toggleHide={toggleHideDevice}
          />
        )}
        {view === "compare" && (
          <HistoricalCharts devices={devices} api={api} notify={notify} t={t} Chart={EChart} analytics />
        )}
        {view === "history" && <HistoricalCharts devices={devices} api={api} notify={notify} t={t} Chart={EChart} />}
        {view === "alerts" && (
          <AlertsPage
            alerts={alerts}
            workOrders={workOrders}
            user={user}
            busy={busy}
            clearAlerts={clearAlerts}
            acknowledgeAlert={acknowledgeAlert}
            openAlertDetail={openAlertDetail}
            openMaintenance={() => safeSetView("maintenance")}
          />
        )}
        {view === "database" && (
          <HistoricalDatabase devices={devices} api={api} notify={notify} t={t} downloadRows={downloadRows} />
        )}
        {view === "logs" && (
          <DataLogsPage devices={devices} api={api} notify={notify} />
        )}
        {view === "maintenance" && (
          <Maintenance
            devices={devices}
            workOrders={workOrders}
            logs={logs}
            user={user}
            submitMaintenance={submitMaintenance}
            busy={busy}
            updateWork={updateWork}
            deleteWorkOrder={deleteWorkOrder}
            updateMaintenanceLog={updateMaintenanceLog}
            deleteMaintenanceLog={deleteMaintenanceLog}
          />
        )}
        {view === "admin" && user.role === "admin" && (
          <Admin
            devices={devices}
            users={users}
            submitWorkOrder={submitWorkOrder}
            submitThreshold={submitThreshold}
            submitModuleStatus={submitModuleStatus}
            api={api}
            notify={notify}
            busy={busy}
            editingDeviceId={editingDeviceId}
            deviceDraft={deviceDraft}
            setDeviceDraft={setDeviceDraft}
            startEditDevice={startEditDevice}
            cancelEdit={() => { setEditingDeviceId(null); setDeviceDraft({}); }}
            saveDevice={saveDevice}
            deleteDevice={deleteDevice}
            selectedDevice={selectedAdminDevice}
            themeMode={themeMode}
            setThemeMode={setThemeMode}
            language={language}
            setLanguage={setLanguage}
            hiddenIds={hiddenIds}
            toggleHide={toggleHideDevice}
            refreshAll={refreshAll}
          />
        )}
      </section>

      {detailDevice && detailModule && (
        <Detail
          device={detailDevice}
          module={detailModule}
          setModuleId={setDetailModuleId}
          close={() => setDetailDeviceId(null)}
          history={history}
          telemetry={detailTelemetry}
          alerts={alerts}
          logs={logs}
          timeRange={detailTimeRange}
          setTimeRange={setDetailTimeRange}
        />
      )}
    </main>
    </TranslationContext.Provider>
  );
}

function Brand({ large = false }) {
  const t = useT();
  return (
    <div className={cls("brand-block", large && "large")}>
      <img src={LOGO} alt="ADI" />
      <div className="brand-copy">
        <span className="brand-company">Analog Devices</span>
        <h1>HT9046MX</h1>
        <p>{t("Predictive maintenance")}</p>
      </div>
    </div>
  );
}

function CommandBar({ view, alertBadgeCount, query, setQuery, openHandlers, openAlerts }) {
  const t = useT();
  return (
    <div className="command-bar">
      <div className="command-actions">
        <form
          className="search-box"
          onSubmit={(event) => {
            event.preventDefault();
            openHandlers();
          }}
        >
          <Search size={16} />
          <input
            placeholder={t("Search sensor ID, location...")}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onFocus={() => view !== "handlers" && openHandlers()}
          />
        </form>
        <button className="icon-alert" type="button" aria-label={t("Alerts")} onClick={openAlerts}>
          <Bell size={17} />
          {alertBadgeCount > 0 && <span>{alertBadgeCount}</span>}
        </button>
      </div>
    </div>
  );
}

function Overview({ summary, devices, workOrders, alerts, api, refresh, refreshing, openAlerts, openHandlersForFilter, openDetail, openMaintenance }) {
  const t = useT();
  const [trendRefreshKey, setTrendRefreshKey] = useState(0);
  const counts = summary?.counts || {};
  const connection = summary?.connection_counts || {};
  const modules = useMemo(() => devices.flatMap((device) => device.modules || []), [devices]);
  const activeAlerts = buildOverviewAlerts(alerts, devices, workOrders);
  const totalDevices = summary?.total_devices || devices.length;
  const goodDevices = counts.NORMAL || 0;
  const warningDevices = (counts.WARNING || 0) + (counts.WATCH || 0);
  const repairDevices = counts.MAINTENANCE_REQUIRED || 0;
  const repairingDevices = counts.UNDER_MAINTENANCE || 0;
  const offlineDevices = counts.OFFLINE || 0;
  const needAttentionDevices = warningDevices + repairDevices;
  const offlineSignalDevices = connection.OFFLINE ?? devices.filter((device) => device.connection_state === "OFFLINE").length;
  const openOrders = workOrders.filter((order) => !["DONE", "CLOSED", "CANCELLED"].includes(order.status)).slice(0, 5);
  const systemStatusBars = [
    { label: "Good", filter: "GOOD", value: goodDevices + (counts.MONITORING || 0), color: COLOR_GOOD },
    { label: "Warning", filter: "WARNING", value: warningDevices, color: COLOR_WARN },
    { label: "Repair now", filter: "REPAIR_NOW", value: repairDevices, color: COLOR_DANGER },
    { label: "Repairing", filter: "REPAIRING", value: repairingDevices, color: COLOR_BLUE },
    { label: "Offline", filter: "OFFLINE", value: offlineDevices, color: COLOR_OFFLINE },
    { label: "Pending", filter: "NOT_EVALUATED", value: counts.NOT_EVALUATED || 0, color: COLOR_OFFLINE },
  ];
  const maxSystemStatus = Math.max(...systemStatusBars.map((item) => item.value), 1);

  return (
    <>
      <div className="section-title">
        <div>
          <span className="eyebrow">ADI predictive maintenance</span>
          <h2>{t("Data Operations Center")}</h2>
        </div>
        <LoadingButton className="ghost-btn" busy={refreshing} busyText="Refreshing" icon={RefreshCcw} onClick={() => { setTrendRefreshKey((value) => value + 1); refresh(); }}>{t("Refresh")}</LoadingButton>
      </div>

      {!summary ? (
        <div className="ops-kpi-grid system-summary-grid">
          <Skeleton height={156} /><Skeleton height={156} /><Skeleton height={156} /><Skeleton height={156} />
        </div>
      ) : (
        <div className="ops-kpi-grid system-summary-grid">
          <SystemKpi icon={AlertTriangle} label={t("Need Attention")} value={needAttentionDevices} sublabel={`${warningDevices} ${t("Warning")} / ${repairDevices} ${t("Repair now")}`} tone={repairDevices ? "danger" : needAttentionDevices ? "warn" : "good"} />
          <SystemKpi icon={Activity} label={t("Offline")} value={offlineSignalDevices} sublabel={`${connection.ONLINE || 0} ${t("Handlers")}`} tone={offlineSignalDevices ? "neutral" : "good"} />
          <SystemKpi icon={Wrench} label={t("Open Work Orders")} value={summary?.open_work_orders || openOrders.length} sublabel={`${repairingDevices} ${t("Repairing")}`} tone={(summary?.open_work_orders || openOrders.length) ? "warn" : "good"} />
          <SystemKpi icon={Server} label={t("Fleet Handlers")} value={totalDevices} sublabel={`${modules.length} ${t("Module")}`} tone="info" />
        </div>
      )}

      <div className="dashboard-grid overview-health-grid">
        <FleetHealthTrend api={api} refreshKey={trendRefreshKey} />
        <article className="panel overview-distribution-panel">
          <div className="panel-head">
            <div>
              <h3>{t("Handler status distribution")}</h3>
              <p className="panel-note">{totalDevices || 0} {t("handlers tracked")}</p>
            </div>
          </div>
          <div className="status-bars">
            {systemStatusBars.map((item) => (
              <button
                className="status-bar-row status-bar-action"
                key={item.label}
                type="button"
                onClick={() => openHandlersForFilter(item.filter)}
                aria-label={`Show ${item.label} handlers`}
              >
                <span>{t(item.label)}</span>
                <div><i style={{ width: `${(item.value / maxSystemStatus) * 100}%`, background: item.color }} /></div>
                <strong>{item.value}</strong>
              </button>
            ))}
          </div>
        </article>
      </div>

      <div className="dashboard-grid overview-module-grid">
        <CompressorHealthMap devices={devices} openDetail={openDetail} openAll={() => openHandlersForFilter("ALL")} />
        <VacuumAttentionList devices={devices} openDetail={openDetail} openAll={() => openHandlersForFilter("ALL")} />
      </div>

      <div className="dashboard-grid overview-system-grid overview-bottom-grid">
        <TopDeteriorating devices={devices} openDetail={openDetail} />
        <article className="panel active-alerts-panel">
          <div className="panel-head">
            <div>
              <h3>{t("Active alerts")}</h3>
              <p className="panel-note">Sorted by severity - updated live</p>
            </div>
            <button className="text-link action-link" type="button" onClick={openAlerts}>{t("View all")}</button>
          </div>
          <AlertFeed rows={activeAlerts} />
        </article>
      </div>

      <div className="dashboard-grid overview-work-grid">
        <article className="panel overview-work-orders-panel">
          <div className="panel-head">
            <div>
              <h3>{t("Open work orders")}</h3>
              <p className="panel-note">{t("Technician actions waiting for update")}</p>
            </div>
            <button className="text-link action-link" type="button" onClick={openMaintenance}>{t("Open Maintenance")} <ChevronRight size={14} /></button>
          </div>
          <OverviewWorkOrderList rows={openOrders} openMaintenance={openMaintenance} />
        </article>
      </div>

    </>
  );
}

function FleetHealthTrend({ api, refreshKey }) {
  const t = useT();
  const range = "7d";
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    setError("");
    const load = () => api(`/api/overview/health-trend?range=${range}`)
      .then((result) => { if (active) setData(result); })
      .catch((cause) => { if (active) setError(String(cause.message || cause)); })
      .finally(() => { if (active) setLoading(false); });
    load();
    const timer=setInterval(load,60000);
    return () => { active = false; clearInterval(timer); };
  }, [api, range, refreshKey]);

  const points = data?.range === range ? data.points || [] : [];
  const hasObservations = points.some((point) => point.observed > 0);
  const option = useMemo(() => ({
    color: [COLOR_GOOD, COLOR_WARN, COLOR_DANGER, COLOR_OFFLINE],
    grid: { left: 34, right: 12, top: 20, bottom: 31 },
    tooltip: {
      trigger: "axis", confine: true,
      formatter: (items) => {
        const point = points[items[0]?.dataIndex];
        if (!point?.observed) return t("No diagnostic coverage");
        return `${new Date(point.at).toLocaleString()}<br/>${items.map((item) => `${item.marker} ${item.seriesName}: ${item.value ?? "—"}`).join("<br/>")}<br/>${t("Observed modules")}: ${point.observed}`;
      },
    },
    xAxis: { type: "category", boundaryGap: false, data: points.map((point) => new Date(point.at).toLocaleString("en-GB", {timeZone:"Asia/Bangkok",month:"2-digit",day:"2-digit",hour:"2-digit",hourCycle:"h23"})), axisTick: { show: false }, axisLabel: { hideOverlap:true }, axisLine: { lineStyle: { color: CHART_GRID } } },
    yAxis: { type: "value", min: 0, minInterval: 1, splitLine: { lineStyle: { color: CHART_GRID } } },
    series: [
      { name: t("Good"), key: "good", color: COLOR_GOOD },
      { name: t("Warning"), key: "warning", color: COLOR_WARN },
      { name: t("Repair now"), key: "repair_now", color: COLOR_DANGER },
      { name: t("Offline"), key: "offline", color: COLOR_OFFLINE },
    ].map((item) => ({ name: item.name, type: "line", data: points.map((point) => point[item.key]), smooth: false, connectNulls: false, symbol: "circle", symbolSize: 4, showSymbol: false, lineStyle: { width: 2.5 }, areaStyle: { opacity: 0.06 }, itemStyle: { color: item.color } })),
  }), [points, range, t]);

  return (
    <article className="panel overview-trend-panel">
      <div className="panel-head overview-trend-head">
        <div><h3>{t("Fleet Health Trend")}</h3><p className="panel-note">{t("Module status at each completed hour · last 7 days")}</p></div>
      </div>
      {loading ? <Skeleton height={242} /> : error ? <div className="overview-trend-state" role="alert">{t("Could not load health trend")}: {error}</div> : !hasObservations ? <div className="overview-trend-state">{t("No diagnostic history in this period")}</div> : <EChart option={option} className="overview-trend-chart" />}
      <div className="overview-trend-footer">
        <div className="overview-trend-legend"><span className="good">{t("Good")}</span><span className="warning">{t("Warning")}</span><span className="repair">{t("Repair now")}</span><span className="offline">{t("Offline")}</span></div>
        <small>{t("Gaps mean no hourly capture; unknown health is not Good")}</small>
      </div>
    </article>
  );
}

function attentionOrder(status) {
  return {
    MAINTENANCE_REQUIRED: 0,
    WARNING: 1,
    WATCH: 1,
    OFFLINE: 2,
    UNDER_MAINTENANCE: 3,
    NORMAL: 4,
    MONITORING: 4,
  }[status] ?? 5;
}

function moduleNumber(module) {
  const match = String(module?.module_code || module?.module_name || "").match(/(?:^|[-_\s])m([1-8])(?:$|[-_\s])/i);
  return match ? Number(match[1]) : null;
}

function CompressorHealthMap({ devices, openDetail, openAll }) {
  const t = useT();
  const [hovered, setHovered] = useState(null);
  useEffect(() => {
    if (!hovered) return undefined;
    const dismiss = () => setHovered(null);
    const handleScroll = () => {
      if (!hovered.keyboard || document.activeElement !== hovered.anchor) return dismiss();
      const rect = hovered.anchor.getBoundingClientRect();
      setHovered(current => current && ({ ...current,
        left: Math.max(12, Math.min(rect.left + rect.width / 2 - 148, window.innerWidth - 308)),
        top: rect.bottom + 10, anchorTop: rect.top, above: window.innerHeight - rect.bottom < 265,
      }));
    };
    window.addEventListener("scroll", handleScroll, true);
    window.addEventListener("resize", dismiss);
    return () => {
      window.removeEventListener("scroll", handleScroll, true);
      window.removeEventListener("resize", dismiss);
    };
  }, [hovered]);
  const showDiagnostic = (event, device, module, status) => {
    const rect = event.currentTarget.getBoundingClientRect();
    setHovered({ device, module, status, anchor: event.currentTarget, keyboard: event.type === "focus",
      left: Math.max(12, Math.min(rect.left + rect.width / 2 - 148, window.innerWidth - 308)),
      top: rect.bottom + 10,
      above: window.innerHeight - rect.bottom < 265,
      anchorTop: rect.top,
    });
  };
  const fleetMachineCount = devices.filter(device => (device.modules || []).some(module => moduleSource(module) === "compressor")).length;
  const rows = devices.map((device) => {
    const modules = (device.connection_state === "OFFLINE" ? (device.modules || []) : activeModules(device)).filter((module) => moduleSource(module) === "compressor");
    const modulePriority = Math.min(...modules.map((module) => attentionOrder(displayModuleStatus(module))));
    return { device, modules, worst: device.connection_state === "ONLINE" ? modulePriority : Math.min(modulePriority, 2) };
  }).filter((row) => row.modules.length).sort((a, b) => a.worst - b.worst || machineTitle(a.device).localeCompare(machineTitle(b.device)));
  const preview = rows.slice(0, 5);

  return (
    <article className="panel module-map-panel">
      <div className="panel-head"><div><h3>{t("Compressor modules")}</h3><p className="panel-note">Machines needing attention first · {preview.length} / {fleetMachineCount}</p></div>{rows.length > 5 && <button className="text-link action-link" type="button" onClick={openAll}>{t("View all")}</button>}</div>
      <div className="compressor-map-legend" aria-label={t("Module status legend")}>
        <span className="good">{t("GOOD")}</span><span className="warning">{t("WARNING")}</span><span className="repair">{t("REPAIR NOW")}</span>
        {rows.some(row => row.modules.some(module => displayModuleStatus(module) === "UNDER_MAINTENANCE")) && <span className="repairing">{t("REPAIRING")}</span>}
        <span className="no-data">{t("No data")}</span><span className="offline">{t("Offline")}</span>
        <span className="no-data">{t("Pending")}</span>
      </div>
      <p className="compressor-map-key">{t("Grey: Offline after 30 minutes without signal")}</p>
      {!rows.length ? <Empty>{t("No compressor modules available")}</Empty> : (
        <div className="compressor-map-scroll">
          <div className="compressor-map-grid map-heading"><span>{t("Machine")}</span>{Array.from({ length: 8 }, (_, index) => <span key={index}>M{index + 1}</span>)}</div>
          {preview.map(({ device, modules }) => (
            <div className="compressor-map-grid" key={device.id}>
              <button className="map-machine" type="button" onClick={() => openDetail(device)}>{machineTitle(device)}</button>
              {Array.from({ length: 8 }, (_, index) => {
                const module = modules.find((item) => moduleNumber(item) === index + 1);
                const status = module && (device.connection_state === "OFFLINE" ? "OFFLINE" : displayModuleStatus(module));
                return module ? (
                  <button key={index} className={cls("map-cell", status)} type="button" onClick={() => { setHovered(null); openDetail(device, module); }}
                    onMouseEnter={event => showDiagnostic(event, device, module, status)} onMouseLeave={() => setHovered(null)}
                    onFocus={event => showDiagnostic(event, device, module, status)} onBlur={() => setHovered(null)}
                    onKeyDown={event => { if (event.key === "Escape") setHovered(null); }}
                    aria-describedby={hovered?.module.id === module.id ? "compressor-module-diagnostic" : undefined}
                    aria-label={`${machineTitle(device)} M${index + 1}: ${t(conditionLabel(status))}`} />
                ) : <span key={index} className="map-cell empty" aria-label={`${machineTitle(device)} M${index + 1}: ${t("No data")}`}>—</span>;
              })}
            </div>
          ))}
        </div>
      )}
      {hovered && createPortal(
        <div id="compressor-module-diagnostic" role="tooltip" className="compressor-module-diagnostic"
          style={{ left: `calc(${hovered.left}px / var(--dashboard-scale))`, ...(hovered.above ? { bottom: `calc(${window.innerHeight - hovered.anchorTop + 10}px / var(--dashboard-scale))` } : { top: `calc(${hovered.top}px / var(--dashboard-scale))` }) }}>
          <strong>{machineTitle(hovered.device)}</strong>
          <span className="diagnostic-module-name">{hovered.module.module_name.replace(/^Compressor\s+/i, "")}</span>
          <dl>
            <div><dt>{t("Status")}</dt><dd>{t(conditionLabel(hovered.status))}</dd></div>
            <div><dt>{t("Health Score")}</dt><dd>{hovered.module.health_score == null || !Number.isFinite(Number(hovered.module.health_score)) ? t("Awaiting ML Score") : `${n(hovered.module.health_score, 0)} / 100`}</dd></div>
            <div><dt>{t("ML result at")}</dt><dd>{dateText(hovered.module.health_score_at)}</dd></div>
            <div><dt>{t("Last sensor reading")}</dt><dd>{dateText(hovered.module.diagnostic_at)}</dd></div>
            <div><dt>{t("Handler signal")}</dt><dd>{t(connectionLabel(hovered.device.connection_state))}</dd></div>
          </dl>
          <small>{t("Select to inspect this module")}</small>
        </div>, document.body
      )}
    </article>
  );
}

function VacuumAttentionList({ devices, openDetail, openAll }) {
  const t = useT();
  const [hovered, setHovered] = useState(null);

  useEffect(() => {
    if (!hovered) return undefined;
    const dismiss = () => setHovered(null);
    const handleScroll = () => {
      if (!hovered.keyboard || document.activeElement !== hovered.anchor) return dismiss();
      const rect = hovered.anchor.getBoundingClientRect();
      setHovered(current => current && ({ ...current,
        left: Math.max(12, Math.min(rect.left + rect.width / 2 - 148, window.innerWidth - 308)),
        top: rect.bottom + 10, anchorTop: rect.top, above: window.innerHeight - rect.bottom < 265,
      }));
    };
    window.addEventListener("scroll", handleScroll, true);
    window.addEventListener("resize", dismiss);
    return () => {
      window.removeEventListener("scroll", handleScroll, true);
      window.removeEventListener("resize", dismiss);
    };
  }, [hovered]);

  const showDiagnostic = (event, device, module, status) => {
    const rect = event.currentTarget.getBoundingClientRect();
    setHovered({
      device,
      module,
      status,
      anchor: event.currentTarget,
      keyboard: event.type === "focus",
      left: Math.max(12, Math.min(rect.left + rect.width / 2 - 148, window.innerWidth - 308)),
      top: rect.bottom + 10,
      above: window.innerHeight - rect.bottom < 265,
      anchorTop: rect.top,
    });
  };

  const rows = devices.flatMap((device) => (device.modules || [])
    .filter((module) => moduleSource(module) === "vacuum")
    .map((module) => ({ device, module, status: displayModuleStatus(module) })))
    .sort((a, b) => Math.min(attentionOrder(a.status), a.device.connection_state === "ONLINE" ? 5 : 2)
      - Math.min(attentionOrder(b.status), b.device.connection_state === "ONLINE" ? 5 : 2)
      || machineTitle(a.device).localeCompare(machineTitle(b.device)));
  const previewMachines = new Set(rows.map((row) => row.device.id).filter((id, index, ids) => ids.indexOf(id) === index).slice(0, 5));
  const preview = rows.filter((row) => previewMachines.has(row.device.id));
  const machineCount = new Set(rows.map((row) => row.device.id)).size;

  return (
    <article className="panel vacuum-attention-panel">
      <div className="panel-head"><div><h3>{t("Vacuum Pump modules")}</h3><p className="panel-note">{t("Machines needing attention first")} · {previewMachines.size} / {machineCount}</p></div>{machineCount > 5 && <button className="text-link action-link" type="button" onClick={openAll}>{t("View all")}</button>}</div>
      {!rows.length ? <Empty>{t("No vacuum modules available")}</Empty> : (
        <div className="vacuum-attention-list">
          {preview.map(({ device, module, status }) => (
            <button
              className="vacuum-attention-row"
              type="button"
              key={`${device.id}-${module.id}`}
              onClick={() => { setHovered(null); openDetail(device, module); }}
              onMouseEnter={(event) => showDiagnostic(event, device, module, status)}
              onMouseLeave={() => setHovered(null)}
              onFocus={(event) => showDiagnostic(event, device, module, status)}
              onBlur={() => setHovered(null)}
              onKeyDown={(event) => { if (event.key === "Escape") setHovered(null); }}
              aria-describedby={hovered?.module.id === module.id ? "vacuum-module-diagnostic" : undefined}
            >
              <span className="vacuum-machine"><strong>{machineTitle(device)}</strong><small>{module.module_name}</small></span>
              <StatusBadge value={status} />
              <span className={cls("vacuum-vibration", status)}><Activity size={15} />{module.vibration == null ? "—" : `${n(module.vibration, 1)} G rms`}</span>
              <ChevronRight size={15} aria-hidden="true" />
            </button>
          ))}
        </div>
      )}
      {hovered && createPortal(
        <div
          id="vacuum-module-diagnostic"
          role="tooltip"
          className="compressor-module-diagnostic"
          style={{
            left: `calc(${hovered.left}px / var(--dashboard-scale))`,
            ...(hovered.above
              ? { bottom: `calc(${window.innerHeight - hovered.anchorTop + 10}px / var(--dashboard-scale))` }
              : { top: `calc(${hovered.top}px / var(--dashboard-scale))` }),
          }}
        >
          <strong>{machineTitle(hovered.device)}</strong>
          <span className="diagnostic-module-name">{hovered.module.module_name}</span>
          <dl>
            <div><dt>{t("Status")}</dt><dd>{t(conditionLabel(hovered.status))}</dd></div>
            <div><dt>{t("Health Score")}</dt><dd>{hovered.module.health_score == null || !Number.isFinite(Number(hovered.module.health_score)) ? t("Awaiting ML Score") : `${n(hovered.module.health_score, 0)} / 100`}</dd></div>
            <div><dt>{t("ML result at")}</dt><dd>{hovered.module.health_score_at ? dateText(hovered.module.health_score_at) : t("Awaiting ML Score")}</dd></div>
            <div><dt>{t("Last sensor reading")}</dt><dd>{dateText(hovered.module.diagnostic_at || hovered.module.recorded_at)}</dd></div>
            <div><dt>{t("Handler signal")}</dt><dd>{t(connectionLabel(hovered.device.connection_state))}</dd></div>
          </dl>
          <small>{t("Select to inspect this module")}</small>
        </div>,
        document.body
      )}
    </article>
  );
}

function TopDeteriorating({ devices, openDetail }) {
  const t = useT();
  const rows = devices.flatMap((device) => (device.modules || []).map((module) => {
    const current = module.health_score == null ? null : Number(module.health_score);
    const baseline = module.health_score_24h_baseline == null ? null : Number(module.health_score_24h_baseline);
    return { device, module, current, delta: current !== null && baseline !== null ? current - baseline : null };
  })).filter((row) => Number.isFinite(row.delta) && row.delta < 0)
    .sort((a, b) => a.delta - b.delta || a.current - b.current).slice(0, 5);
  return (
    <article className="panel deteriorating-panel">
      <div className="panel-head"><div><h3>{t("Top deteriorating modules")}</h3><p className="panel-note">{t("Health Score vs 24–48h baseline")}</p></div></div>
      {!rows.length ? <Empty>{t("No comparable score declines")}</Empty> : (
        <div className="deteriorating-list">
          {rows.map(({ device, module, current, delta }, index) => (
            <button className="deteriorating-row" type="button" key={`${device.id}-${module.id}`} onClick={() => openDetail(device, module)}>
              <span className="deteriorating-rank">{index + 1}</span>
              <span className="deteriorating-name"><strong>{machineTitle(device)} / {module.module_name}</strong><small>{t(moduleSource(module) === "compressor" ? "Compressor" : "Vacuum Pump")}</small></span>
              <strong>{n(current, 0)}</strong><span className="score-decline">{n(delta, 0)}</span>
            </button>
          ))}
        </div>
      )}
    </article>
  );
}

function SystemKpi({ icon: Icon, label, value, sublabel, tone }) {
  const longValue = String(value ?? "").length > 9;
  return (
    <article className={cls("system-kpi", tone, longValue && "long-value")}>
      <div className="kpi-icon"><Icon size={18} /></div>
      <span>{label}</span>
      <strong>{value}</strong>
      <p>{sublabel}</p>
    </article>
  );
}

function OverviewWorkOrderList({ rows, openMaintenance }) {
  const t = useT();
  if (!rows.length) return <Empty>{t("No open work orders")}</Empty>;
  return (
    <div className="overview-work-order-list">
      {rows.map((row) => (
        <button className={cls("overview-work-order", String(row.priority || "").toLowerCase())} type="button" key={row.id} onClick={openMaintenance}>
          <span className="overview-work-order-icon"><Wrench size={16} /></span>
          <span className="overview-work-order-main"><strong>{row.title || t("Maintenance task")}</strong><small>{row.machine_code || row.display_name || row.device_name || t("Handler")} / {row.module_name || t("All modules")}</small></span>
          <span className="overview-order-badges"><span className={cls("overview-order-priority", String(row.priority || "MEDIUM").toLowerCase())}>{t(row.priority || "MEDIUM")}</span><span className="overview-order-status">{t(row.status === "IN_PROGRESS" ? "In progress" : "Open")}</span></span>
          <ChevronRight size={17} aria-hidden="true" />
        </button>
      ))}
    </div>
  );
}

function ScoreRing({ score }) {
  const safeScore = Math.max(0, Math.min(100, Number(score) || 0));
  return (
    <div className="score-ring" style={{ "--score": `${safeScore}%` }}>
      <strong>{n(safeScore, 0)}</strong>
      <span>of 100</span>
    </div>
  );
}

function SensorTrendCard({ icon: Icon, label, value, unit, range, color, option }) {
  const t = useT();
  return (
    <article className="sensor-trend-card" style={{ "--sensor-color": color }}>
      <div className="sensor-card-head">
        <div><Icon size={17} /><strong>{t(label)}</strong></div>
        <span>{t(range)}</span>
      </div>
      <div className="sensor-card-value" style={{ color }}>{value}<em>{unit}</em></div>
      {option ? <EChart option={option} className="sparkline" /> : <div className="sparkline" />}
    </article>
  );
}

function AlertFeed({ rows }) {
  const t = useT();
  if (!rows.length) return <Empty>{t("No active alerts")}</Empty>;
  return (
    <div className="alert-feed">
      {rows.slice(0, 5).map((row) => (
        <div className="alert-row" key={row.id}>
          <span className={cls("alert-icon", row.severity)}><AlertTriangle size={18} /></span>
          <div>
            <strong>{row.title}</strong>
            <p>{row.device} · {row.age}</p>
          </div>
          <span className={cls("severity-pill", row.severity)}>{t(row.severity === "critical" ? "Repair now" : row.severity === "warning" ? "Warning" : "Info")}</span>
        </div>
      ))}
    </div>
  );
}

function AlertsPage({ alerts, workOrders, user, busy, clearAlerts, acknowledgeAlert, openAlertDetail, openMaintenance }) {
  const t = useT();
  const ordersByAlert = useMemo(() => new Map(workOrders.filter((order) => order.source_alert_id).map((order) => [Number(order.source_alert_id), order])), [workOrders]);
  const [severityFilter, setSeverityFilter] = useState("ALL");
  const stats = useMemo(() => ({
    total: alerts.length,
    critical: alerts.filter((alert) => alert.severity === "critical").length,
    warning: alerts.filter((alert) => alert.severity === "warning").length,
    active: alerts.filter((alert) => !alert.acknowledged).length,
  }), [alerts]);
  const filtered = useMemo(() => {
    const rows = severityFilter === "ALL" ? alerts : alerts.filter((alert) => alert.severity === severityFilter);
    return [...rows].sort((a, b) => new Date(b.recorded_at).getTime() - new Date(a.recorded_at).getTime());
  }, [alerts, severityFilter]);

  return (
    <>
      <div className="section-title">
        <div>
          <span className="eyebrow">{t("Alert history")}</span>
          <h2>{t("Alerts")}</h2>
        </div>
        {user?.role === "admin" && (
          <div className="alert-admin-actions">
            <LoadingButton className="danger-btn" busy={busy["alerts:clear"]} busyText="Clearing" icon={Trash2} onClick={clearAlerts}>
              {t("Clear records")}
            </LoadingButton>
          </div>
        )}
      </div>

      <div className="ops-kpi-grid alert-summary-grid">
        <SystemKpi icon={Bell} label={t("Total Alerts")} value={stats.total} sublabel={t("Last 500 records")} tone="info" />
        <SystemKpi icon={AlertTriangle} label={t("Repair now")} value={stats.critical} sublabel={t("Immediate response")} tone={stats.critical ? "danger" : "good"} />
        <SystemKpi icon={AlertTriangle} label={t("Warning")} value={stats.warning} sublabel={t("Needs review")} tone={stats.warning ? "warn" : "good"} />
        <SystemKpi icon={Check} label={t("Active")} value={stats.active} sublabel={t("Not acknowledged")} tone={stats.active ? "warn" : "good"} />
      </div>

      <article className="panel alerts-history-panel">
        <div className="panel-head">
          <div>
            <h3>{t("Alert records")}</h3>
            <p className="panel-note">{filtered.length} events shown</p>
          </div>
          <div className="filter-tabs compact">
            {["ALL", "critical", "warning", "info"].map((item) => (
              <button key={item} className={severityFilter === item ? "active" : ""} onClick={() => setSeverityFilter(item)}>
                {item === "ALL" ? t("All") : t(item === "critical" ? "Repair now" : item === "warning" ? "Warning" : "Info")}
              </button>
            ))}
          </div>
        </div>
        {filtered.length ? (
          <div className="alerts-history-list">
            {filtered.map((alert) => (
              <div className={cls("alert-history-row", alert.acknowledged && "acknowledged")} key={alert.id}>
                <span className={cls("alert-icon", alert.severity || "info")}><AlertTriangle size={18} /></span>
                <button className="alert-history-copy" type="button" onClick={() => openAlertDetail(alert)}>
                  <strong>{alert.title}</strong>
                  <p>{alert.message || t("No message")}</p>
                  <small>{alert.display_name || alert.machine_code || `Device ${alert.device_id}`} · {alert.module_name || "Module"} · {dateText(alert.recorded_at)}</small>
                </button>
                <div className="alert-row-actions">
                  <span className={cls("severity-pill", alert.severity || "info")}>{alert.severity || "info"}</span>
                  {alert.severity === "critical" && ordersByAlert.get(Number(alert.id)) && (
                    <button className="ghost-btn alert-work-link" type="button" onClick={openMaintenance}>
                      {t("Work order")} #{ordersByAlert.get(Number(alert.id)).id}
                    </button>
                  )}
                  {alert.acknowledged ? (
                    <span className="acknowledged-label"><Check size={14} />{t("Acknowledged until")} {dateText(alert.suppressed_until)}</span>
                  ) : (
                    <LoadingButton
                      className="ghost-btn acknowledge-btn"
                      busy={busy[`alert:ack:${alert.id}`]}
                      busyText="Saving"
                      icon={Check}
                      onClick={() => acknowledgeAlert(alert.id)}
                    >
                      {t(alert.severity === "critical" ? "Acknowledge + create work order" : "Acknowledge")}
                    </LoadingButton>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : <Empty>{t("No alerts in this filter")}</Empty>}
      </article>
    </>
  );
}

function Handlers({ devices, filter, setFilter, searchQuery, openDetail, hiddenIds = [] }) {
  const t = useT();
  const query = searchQuery.trim().toLowerCase();

  const visibleDevices = useMemo(() => {
    return devices.filter((device) => {
      return !hiddenIds.includes(device.id) && !hiddenIds.includes(device.machine_code) && !hiddenIds.includes(device.device_uid);
    });
  }, [devices, hiddenIds]);

  const filterOptions = useMemo(() => HANDLER_FILTER_OPTIONS.map((option) => ({
    ...option,
    count: visibleDevices.filter((device) => handlerMatchesFilter(device, option.key)).length,
  })), [visibleDevices]);

  const filtered = visibleDevices.filter((device) => {
    if (!handlerMatchesFilter(device, filter)) return false;
    if (!query) return true;
    const searchable = [
      machineTitle(device),
      device.display_name,
      device.machine_code,
      device.device_uid,
      device.location,
      device.status,
      ...(device.modules || []).flatMap((module) => [module.module_name, module.module_code, module.status]),
    ];
    return searchable.some((value) => String(value || "").toLowerCase().includes(query));
  });

  useEffect(() => {
    if (!HANDLER_FILTER_BY_KEY[filter]) setFilter("ALL");
  }, [filter, setFilter]);

  return (
    <>
      <div className="section-title">
        <div>
          <span className="eyebrow">{t("Handler Telemetry Nodes")}</span>
          <h2>{t("Handlers")}</h2>
        </div>
        <div className="filter-tabs">
          {filterOptions.map((item) => (
            <button key={item.key} className={filter === item.key ? "active" : ""} onClick={() => setFilter(item.key)}>
              {t(item.label)}
              <span className="filter-count">{item.count}</span>
            </button>
          ))}
        </div>
      </div>
      <div className="handler-grid">
        {!devices.length ? (
          <><Skeleton height={220} /><Skeleton height={220} /><Skeleton height={220} /></>
        ) : filtered.length ? filtered.map((device) => (
          <HandlerCard
            key={device.id}
            device={device}
            openDetail={openDetail}
          />
        )) : <Empty>{t("No handlers match the current filter")}</Empty>}
      </div>
    </>
  );
}

function HandlerCard({ device, openDetail }) {
  const t = useT();
  const modules = device.modules || [];
  const groups = groupedModules(device);
  const unregistered = isUnregisteredDevice(device);
  const connectionState = unregistered ? "UNREGISTERED" : device.connection_state;
  return (
    <article
      className={cls("handler-card", unregistered && "unregistered")}
      role="button"
      tabIndex={0}
      onClick={() => openDetail(device)}
      onKeyDown={(event) => {
        if (event.key === "Enter" || event.key === " ") {
          event.preventDefault();
          openDetail(device);
        }
      }}
    >
      <div className="handler-head">
        <div>
          <h3>{machineTitle(device)}</h3>
          <div className="device-id">{device.device_uid || device.machine_code}</div>
          {device.location && <div className="handler-location"><MapPin size={13} />{device.location}</div>}
        </div>
        <div className="handler-status-stack">
          <StatusBadge value={displayDeviceStatus(device)} />
        </div>
      </div>
      <ConnectionBadge state={connectionState} seconds={device.seconds_since_seen} />
      <div className="source-group-list">
        {groups.length ? groups.map((group) => (
          <section className="source-group" key={group.source}>
            <div className="module-row source-overview-row">
              <div>
                <strong>Module {group.label}</strong>
                <small>{t(group.source === "compressor" ? "Open to view M1–M8" : "Vacuum telemetry")}</small>
              </div>
              <StatusBadge value={displayModuleStatus(worstModule({ modules: group.modules }) || group.modules[0])} />
            </div>
          </section>
        )) : (
          <div className="module-row unregistered-row">
            <span>{t("No active module in the latest MySQL row")}</span>
            <StatusBadge value="UNREGISTERED" />
          </div>
        )}
      </div>
      <div className="handler-card-action">
        <span>{t(modules.length ? "Open handler modules" : "Configure module")}</span>
        <ChevronRight size={16} />
      </div>
    </article>
  );
}

function MiniMetric({ label, value }) {
  return <div className="mini-metric"><span>{label}</span><strong>{value}</strong></div>;
}

function DataLogsPage({ devices, api, notify }) {
  const t = useT();
  const [deviceId, setDeviceId] = useState("");
  const [offset, setOffset] = useState(0);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(null);
  useEffect(() => {
    let active = true;
    setLoading(true);
    api(`/api/maintenance-logs?limit=50&offset=${offset}${deviceId ? `&device_id=${deviceId}` : ""}`)
      .then((data) => { if (active) setRows(data); })
      .catch((error) => { if (active) notify("error", "Could not load maintenance logs", String(error.message || error)); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [api, notify, offset, deviceId]);
  return <>
    <div className="section-title"><div><span className="eyebrow">{t("Data")}</span><h2>{t("Maintenance Logs")}</h2></div></div>
    <article className="panel data-logs-panel">
      <div className="panel-head"><h3>{t("Detailed service records")}</h3><label className="data-logs-filter">{t("Device")}<select value={deviceId} onChange={(event) => { setDeviceId(event.target.value); setOffset(0); }}><option value="">{t("All devices")}</option>{devices.map((device) => <option key={device.id} value={device.id}>{device.display_name || device.machine_code}</option>)}</select></label></div>
      {loading ? <Skeleton height={240} /> : rows.length ? <div className="data-logs-list">{rows.map((log) => <div className="data-log-item" key={log.id}>
        <button type="button" className="data-log-heading" onClick={() => setExpanded(expanded === log.id ? null : log.id)} aria-expanded={expanded === log.id}>
          <span><strong>#{log.id} · {log.display_name || log.machine_code}</strong><small>{dateText(log.recorded_at)} · {log.module_name || t("All modules")} · {log.work_order_id ? `${t("Work Order")} #${log.work_order_id}` : t("No linked work order")}</small></span>
          <strong>{Number(log.cost_baht || 0).toLocaleString()} {t("Baht")}</strong><ChevronRight size={16} />
        </button>
        {expanded === log.id && <IncidentReportContext context={log.incident_context} />}
        {expanded === log.id && <div className="data-log-detail"><p><strong>{t("Technician")}:</strong> {log.technician_name}</p><p><strong>{t("Description")}:</strong> {log.action_taken}</p><h4>{t("Parts Used")}</h4>{log.parts?.length ? <div className="table-wrap"><table className="data-table"><thead><tr><th>{t("Part name")}</th><th>{t("Quantity")}</th><th>{t("Unit cost (Baht)")}</th><th>{t("Line total")}</th></tr></thead><tbody>{log.parts.map((part, index) => <tr key={index}><td>{part.name}</td><td>{part.quantity}</td><td>{Number(part.unit_cost_baht || 0).toLocaleString()}</td><td>{Number(part.line_cost_baht || 0).toLocaleString()}</td></tr>)}</tbody></table></div> : <p>{log.parts_used || t("No parts used")}</p>}{log.parts_json == null && Number(log.cost_baht) > 0 ? <p>{t("Legacy cost (unitemized)")}: {Number(log.cost_baht).toLocaleString()} {t("Baht")}</p> : <p>{t("Other / labor cost (Baht)")}: {Number(log.other_cost_baht || 0).toLocaleString()}</p>}<p><strong>{t("Total cost")}: {Number(log.cost_baht || 0).toLocaleString()} {t("Baht")}</strong></p></div>}
      </div>)}</div> : <Empty>{t("No maintenance logs yet")}</Empty>}
      <div className="pagination-actions"><button type="button" className="ghost-btn" disabled={offset === 0 || loading} onClick={() => setOffset(Math.max(0, offset - 50))}>{t("Previous")}</button><span>{offset + 1}–{offset + rows.length}</span><button type="button" className="ghost-btn" disabled={rows.length < 50 || loading} onClick={() => setOffset(offset + 50)}>{t("Next")}</button></div>
    </article>
  </>;
}

function EditMaintenanceLogForm({ log, busy, onCancel, onSave }) {
  const t = useT();
  const [parts, setParts] = useState((log.parts || []).map((part) => ({ name: part.name, quantity: part.quantity, unit_cost_baht: part.unit_cost_baht })));
  const submit = (event) => {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    onSave({ technician_name: form.get("technician_name"), action_taken: form.get("action_taken"), parts, parts_used: log.parts_used || "", other_cost_baht: Number(form.get("other_cost_baht") || 0) }).catch(() => {});
  };
  return <form className="edit-log-form" onSubmit={submit}><h4>{t("Edit maintenance log")} #{log.id}</h4><label>{t("Technician")}<input name="technician_name" defaultValue={log.technician_name} required /></label><label>{t("Description")}<textarea name="action_taken" rows="3" defaultValue={log.action_taken} required /></label><div className="panel-head"><strong>{t("Parts Used")}</strong><button type="button" className="ghost-btn" onClick={() => setParts([...parts, { name: "", quantity: 1, unit_cost_baht: 0 }])}><Plus size={14} /> {t("Add used part")}</button></div>{parts.map((part, index) => <div className="part-entry" key={index}><label>{t("Part name")}<input required value={part.name} onChange={(event) => setParts(parts.map((item, i) => i === index ? { ...item, name: event.target.value } : item))} /></label><label>{t("Quantity")}<input required type="number" min="0.01" step="any" value={part.quantity} onChange={(event) => setParts(parts.map((item, i) => i === index ? { ...item, quantity: event.target.value } : item))} /></label><label>{t("Unit cost (Baht)")}<input required type="number" min="0" step="0.01" value={part.unit_cost_baht} onChange={(event) => setParts(parts.map((item, i) => i === index ? { ...item, unit_cost_baht: event.target.value } : item))} /></label><button type="button" className="ghost-btn" title={t("Remove part")} onClick={() => setParts(parts.filter((_, i) => i !== index))}><X size={16} /></button></div>)}<label>{t("Other / labor cost (Baht)")}<input name="other_cost_baht" type="number" min="0" step="0.01" defaultValue={log.parts_json == null ? Number(log.cost_baht || 0) : Number(log.other_cost_baht || 0)} /></label><div className="edit-log-actions"><button type="button" className="ghost-btn" onClick={onCancel}>{t("Cancel")}</button><LoadingButton type="submit" busy={busy} busyText={t("Saving")} icon={Save}>{t("Save")}</LoadingButton></div></form>;
}

function Maintenance({ devices, workOrders, logs, user, submitMaintenance, busy, updateWork, deleteWorkOrder, updateMaintenanceLog, deleteMaintenanceLog }) {
  const t = useT();
  const [deviceId, setDeviceId] = useState("");
  const [moduleId, setModuleId] = useState("");
  const [workOrderId, setWorkOrderId] = useState("");
  const [parts, setParts] = useState([]);
  const [editingLog, setEditingLog] = useState(null);
  const selectedDevice = devices.find((d) => String(d.id) === String(deviceId)) || devices[0];
  const modules = selectedDevice?.modules || [];
  const activeOrders = workOrders.filter((w) => w.status !== "DONE" && w.status !== "CANCELLED")
    .sort((a, b) => new Date(a.created_at || 0) - new Date(b.created_at || 0) || a.id - b.id);
  const deviceOrders = activeOrders.filter((w) => !selectedDevice || w.device_id === selectedDevice.id);

  useEffect(() => {
    if (!deviceId && devices[0]) setDeviceId(String(devices[0].id));
  }, [deviceId, devices]);

  useEffect(() => {
    if (!modules.some((module) => String(module.id) === moduleId)) {
      setModuleId(modules[0] ? String(modules[0].id) : "");
    }
    if (workOrderId && !deviceOrders.some((order) => String(order.id) === workOrderId)) {
      setWorkOrderId("");
    }
  }, [modules, deviceOrders, moduleId, workOrderId]);

  const selectWorkOrder = (nextId) => {
    setWorkOrderId(nextId);
    const order = deviceOrders.find((item) => String(item.id) === nextId);
    if (order?.module_id) setModuleId(String(order.module_id));
  };
  const prepareServiceLog = (order) => {
    setDeviceId(String(order.device_id));
    setModuleId(order.module_id ? String(order.module_id) : "");
    setWorkOrderId(String(order.id));
    document.getElementById("maintenance-service-log")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <>
      <div className="section-title">
        <div>
          <span className="eyebrow">{t("Technician workflow")}</span>
          <h2>{t("Maintenance")}</h2>
        </div>
      </div>
      <div className="work-grid">
        <article className="panel assigned-work-panel">
          <div className="panel-head assigned-work-head">
            <div>
              <span className="eyebrow">{t("Work queue")}</span>
              <h3>{t("Assigned Work")}</h3>
            </div>
            <span className="assigned-work-count">{activeOrders.length} {t("active")}</span>
          </div>
          <WorkOrderList orders={activeOrders} updateWork={updateWork} prepareServiceLog={prepareServiceLog} deleteWorkOrder={deleteWorkOrder} isAdmin={user.role === "admin"} busy={busy} />
        </article>
        <form id="maintenance-service-log" className="panel form-grid" onSubmit={(event) => submitMaintenance(event, parts, () => setParts([]))}>
          <div className="panel-head full"><h3>{t("Service Log")}</h3></div>
          <label>
            {t("Select Device")}
            <select name="device_id" value={deviceId} onChange={(e) => { setDeviceId(e.target.value); setWorkOrderId(""); setModuleId(""); }} required>
              {devices.map((d) => <option key={d.id} value={d.id}>{d.display_name || d.machine_code}</option>)}
            </select>
          </label>
          <label>
            {t("Select Module")}
            <select name="module_id" value={moduleId} onChange={(e) => {
              const nextModuleId = e.target.value;
              setModuleId(nextModuleId);
              const linkedOrder = deviceOrders.find((order) => String(order.id) === workOrderId);
              if (linkedOrder?.module_id && String(linkedOrder.module_id) !== nextModuleId) setWorkOrderId("");
            }}>
              {modules.map((m) => <option key={m.id} value={m.id}>{m.module_name}</option>)}
            </select>
          </label>
          <label>
            {t("Work Order")}
            <select name="work_order_id" value={workOrderId} onChange={(e) => selectWorkOrder(e.target.value)}>
              <option value="">{t("No linked work order")}</option>
              {deviceOrders.map((w) => <option key={w.id} value={w.id}>{w.title}</option>)}
            </select>
          </label>
          <label>
            {t("Technician")}
            <input name="technician_name" defaultValue={user.full_name || user.username} />
          </label>
          <label className="full">
            {t("Description")}
            <textarea name="action_taken" rows="4" required placeholder={t("Describe completed maintenance work")} />
          </label>
          <div className="full parts-section">
            <div className="panel-head"><strong>{t("Parts Used")}</strong><button type="button" className="ghost-btn" onClick={() => setParts([...parts, { name: "", quantity: 1, unit_cost_baht: 0 }])}><Plus size={14} /> {t("Add used part")}</button></div>
            {parts.map((part, index) => <div className="part-entry" key={index}>
              <label>{t("Part name")}<input required value={part.name} onChange={(event) => setParts(parts.map((item, i) => i === index ? { ...item, name: event.target.value } : item))} /></label>
              <label>{t("Quantity")}<input required type="number" min="0.01" step="any" value={part.quantity} onChange={(event) => setParts(parts.map((item, i) => i === index ? { ...item, quantity: event.target.value } : item))} /></label>
              <label>{t("Unit cost (Baht)")}<input required type="number" min="0" step="0.01" value={part.unit_cost_baht} onChange={(event) => setParts(parts.map((item, i) => i === index ? { ...item, unit_cost_baht: event.target.value } : item))} /></label>
              <button type="button" className="ghost-btn" title={t("Remove part")} aria-label={t("Remove part")} onClick={() => setParts(parts.filter((_, i) => i !== index))}><X size={16} /></button>
            </div>)}
          </div>
          <label>
            {t("Other / labor cost (Baht)")}
            <input name="other_cost_baht" type="number" min="0" step="0.01" defaultValue="0" />
          </label>
          <p className="maintenance-cost-note">{t("Parts cost")}: {parts.reduce((sum, part) => sum + (Number(part.quantity) || 0) * (Number(part.unit_cost_baht) || 0), 0).toLocaleString()} {t("Baht")} · {t("Total also includes other / labor cost")}</p>
          <LoadingButton className="primary-btn full" busy={busy["maintenance:create"]} busyText="Committing" icon={Save} type="submit">
            {t("Commit Service Log")}
          </LoadingButton>
        </form>
      </div>
      <article className="panel maintenance-logs-panel">
        <div className="panel-head"><h3>{t("Maintenance Logs")}</h3></div>
        <LogTable logs={logs} isAdmin={user.role === "admin"} busy={busy} editLog={setEditingLog} deleteLog={deleteMaintenanceLog} />
        {editingLog && <EditMaintenanceLogForm key={editingLog.id} log={editingLog} busy={busy[`maintenance:edit:${editingLog.id}`]} onCancel={() => setEditingLog(null)} onSave={async (body) => { await updateMaintenanceLog(editingLog.id, body); setEditingLog(null); }} />}
      </article>
    </>
  );
}

function WorkOrderList({ orders, updateWork, prepareServiceLog, deleteWorkOrder, isAdmin = false, busy = {} }) {
  const t = useT();
  if (!orders.length) return <Empty>{t("No active work orders to display")}</Empty>;
  return (
    <div className="work-list assigned-work-list">
      {orders.map((order) => (
        <article className="work-item assigned-work-item" key={order.id}>
          <div className="assigned-work-topline">
            <span className="assigned-work-reference">{t("Work order")} #{order.id}</span>
            <span className={cls("assigned-work-status", order.status === "IN_PROGRESS" ? "in-progress" : "open")}>{t(order.status === "IN_PROGRESS" ? "In progress" : "Open")}</span>
          </div>
          {order.source_alert_id && <span className="assigned-work-origin">{t("From acknowledged alert")} #{order.source_alert_id}</span>}
          {order.report_origin === "ADMIN_WORK_ORDER" && <span className="assigned-work-origin">{t("Reported through Dashboard")}</span>}
          <span className="assigned-work-origin">{order.alert_recorded_at ? t("Alert received") : t("Opened")}: {dateText(order.alert_recorded_at || order.created_at)}</span>
          <h4>{order.title}</h4>
          <div className="assigned-work-details">
            <div><span>{t("Machine")}</span><strong>{order.display_name || order.machine_code || t("Unspecified")}</strong></div>
            <div><span>{t("Module")}</span><strong>{order.module_name || t("All modules")}</strong></div>
            <div><span>{t("Assigned to")}</span><strong>{order.assigned_full_name || order.assigned_username || t("Unassigned")}</strong></div>
          </div>
          {order.description && <p className="assigned-work-description">{order.description}</p>}
          <p className="assigned-work-origin">{t("Observed problem period")}: {order.event_started_at
            ? `${String(order.event_started_at).replace("T", " ")} → ${order.event_ended_at ? String(order.event_ended_at).replace("T", " ") : t("End unknown")} (${order.event_timezone}; ${t(order.event_time_precision)})`
            : t("Onset unknown — not inferred from work creation time")}</p>
          <div className="work-actions assigned-work-actions">
            {isAdmin && deleteWorkOrder && <div className="assigned-work-delete"><LoadingButton className="ghost-btn" busy={busy[`work:delete:${order.id}`]} busyText={t("Deleting")} icon={Trash2} onClick={() => deleteWorkOrder(order.id)}>{t("Delete work order")}</LoadingButton></div>}
            {updateWork && (
              <div className="assigned-work-buttons">
                {order.status !== "IN_PROGRESS" && (
                  <LoadingButton
                    className="ghost-btn assigned-work-start"
                    busy={busy[`work:${order.id}:IN_PROGRESS`]}
                    busyText="Starting"
                    onClick={() => updateWork(order.id, "IN_PROGRESS")}
                  >
                    {t("Start work")}
                  </LoadingButton>
                )}
                {prepareServiceLog && <button className="ghost-btn assigned-work-complete" type="button" onClick={() => prepareServiceLog(order)}>{t("Record service log")}</button>}
              </div>
            )}
          </div>
        </article>
      ))}
    </div>
  );
}

function IncidentReportContext({ context }) {
  const t = useT();
  if (!context) return null;
  const origin = context.report_origin === "ALERT_LINKED" ? "Alert-linked report"
    : context.report_origin === "ADMIN_WORK_ORDER" ? "Manual report" : "Report origin unknown";
  return <details className="incident-report-context">
    <summary>{t("Original incident report")}</summary>
    <p>{t(origin)} · {context.description || t("Unspecified")}</p>
    <small>{t("Observed problem period")}: {context.event_started_at
      ? `${String(context.event_started_at).replace("T", " ")} → ${context.event_ended_at ? String(context.event_ended_at).replace("T", " ") : t("End unknown")} (${context.event_timezone}; ${t(context.event_time_precision || "UNKNOWN")})`
      : t("Onset unknown — not inferred from work creation time")}</small>
  </details>;
}

function LogTable({ logs, isAdmin = false, busy = {}, editLog, deleteLog }) {
  const t = useT();
  if (!logs.length) return <Empty>{t("No maintenance logs yet")}</Empty>;
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead><tr><th>{t("Date")}</th><th>{t("Work Order")}</th><th>{t("Device")}</th><th>{t("Module")}</th><th>{t("Technician")}</th><th>{t("Description")}</th><th>{t("Total cost")}</th>{isAdmin && <th>{t("Action")}</th>}</tr></thead>
        <tbody>
          {logs.map((log) => (
            <tr key={log.id}>
              <td>{dateText(log.recorded_at)}</td>
              <td>{log.work_order_id ? `#${log.work_order_id}` : "—"}</td>
              <td>{log.display_name || log.machine_code}</td>
              <td>{log.module_name || "-"}</td>
              <td>{log.technician_name}</td>
              <td>{log.action_taken}<IncidentReportContext context={log.incident_context} /></td>
              <td>{Number(log.cost_baht || 0).toLocaleString()} {t("Baht")}</td>
              {isAdmin && <td><div className="log-row-actions"><button type="button" className="ghost-btn" title={`${t("Edit maintenance log")} #${log.id}`} aria-label={`${t("Edit maintenance log")} #${log.id}`} onClick={() => editLog(log)}><Edit3 size={15} /></button><LoadingButton className="ghost-btn log-delete-btn" busy={busy[`maintenance:delete:${log.id}`]} busyText={t("Deleting")} icon={Trash2} title={`${t("Delete maintenance log")} #${log.id}`} aria-label={`${t("Delete maintenance log")} #${log.id}`} onClick={() => deleteLog(log.id)} /></div></td>}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Admin(props) {
  const t = useT();
  const {
    devices,
    users,
    submitWorkOrder,
    submitThreshold,
    submitModuleStatus,
    api,
    notify,
    busy,
    editingDeviceId,
    deviceDraft,
    setDeviceDraft,
    startEditDevice,
    cancelEdit,
    saveDevice,
    deleteDevice,
    themeMode,
    setThemeMode,
    language,
    setLanguage,
    hiddenIds = [],
    toggleHide,
    refreshAll,
  } = props;
  const [numbering, setNumbering] = useState(null);
  const [numberingLoading, setNumberingLoading] = useState(false);
  const [resettingTarget, setResettingTarget] = useState(null);

  const loadNumbering = useCallback(async () => {
    setNumberingLoading(true);
    try {
      const data = await api("/api/admin/numbering");
      setNumbering(data);
    } catch (err) {
      console.error("Failed to load numbering:", err);
    } finally {
      setNumberingLoading(false);
    }
  }, [api]);

  useEffect(() => {
    loadNumbering();
  }, [loadNumbering]);

  const handleResetNumbering = async (target) => {
    const targetLabel = target === "alerts"
      ? t("Alert #")
      : target === "work_orders"
      ? t("Work Order #")
      : t("Alert # and Work Order #");

    const confirmMsg = target === "alerts"
      ? t("Are you sure you want to clear all alerts and reset Alert # to 1?")
      : target === "work_orders"
      ? t("Are you sure you want to archive work orders and reset Work Order # to 1? (Historical maintenance logs are kept intact)")
      : t("Are you sure you want to reset both Alert # and Work Order # to 1?");

    if (!window.confirm(confirmMsg)) return;

    setResettingTarget(target);
    try {
      const res = await api("/api/admin/numbering/reset", {
        method: "POST",
        body: { target },
      });
      notify("success", t("Sequence Reset"), `${targetLabel} ${t("has been reset to #1 successfully.")}`);
      if (res?.status) {
        setNumbering(res.status);
      } else {
        loadNumbering();
      }
      if (refreshAll) refreshAll();
    } catch (err) {
      notify("error", t("Sequence Reset Failed"), err.message);
    } finally {
      setResettingTarget(null);
    }
  };
  const [workDeviceId, setWorkDeviceId] = useState("");
  const [thresholdDeviceId, setThresholdDeviceId] = useState("");
  const [thresholdModuleId, setThresholdModuleId] = useState("");
  const [statusDeviceId, setStatusDeviceId] = useState("");
  const [statusModuleId, setStatusModuleId] = useState("");
  const [productionOpen, setProductionOpen] = useState(false);
  const [productionStatus, setProductionStatus] = useState(null);
  const [productionLoading, setProductionLoading] = useState(false);
  const workDevice = devices.find((d) => String(d.id) === String(workDeviceId)) || devices[0];
  const thresholdDevice = devices.find((d) => String(d.id) === String(thresholdDeviceId)) || devices[0];
  const statusDevice = devices.find((d) => String(d.id) === String(statusDeviceId)) || devices[0];
  const thresholdModules = thresholdDevice?.modules || [];
  const thresholdModule = thresholdModules.find((m) => String(m.id) === String(thresholdModuleId)) || thresholdModules[0];
  const statusModules = statusDevice?.modules || [];
  const statusModule = statusModules.find((m) => String(m.id) === String(statusModuleId)) || statusModules[0];
  const tv = (metric, key, fallback) => thresholdModule?.thresholds?.[metric]?.[key] ?? fallback;
  const thresholdIsCompressor = moduleSource(thresholdModule) === "compressor";
  const thresholdEnabled = thresholdModule?.thresholds?.enabled ?? Boolean(Object.keys(thresholdModule?.thresholds || {}).length);

  useEffect(() => {
    if (!workDeviceId && devices[0]) setWorkDeviceId(String(devices[0].id));
    if (!thresholdDeviceId && devices[0]) setThresholdDeviceId(String(devices[0].id));
    if (!statusDeviceId && devices[0]) setStatusDeviceId(String(devices[0].id));
  }, [devices, statusDeviceId, thresholdDeviceId, workDeviceId]);

  useEffect(() => {
    if (thresholdModules.length && !thresholdModules.some((module) => String(module.id) === String(thresholdModuleId))) {
      setThresholdModuleId(String(thresholdModules[0].id));
    }
  }, [thresholdModuleId, thresholdModules]);

  useEffect(() => {
    if (statusModules.length && !statusModules.some((module) => String(module.id) === String(statusModuleId))) {
      setStatusModuleId(String(statusModules[0].id));
    }
  }, [statusModuleId, statusModules]);

  const loadProductionStatus = useCallback(async () => {
    setProductionLoading(true);
    try {
      setProductionStatus(await api("/api/production/status"));
    } catch (error) {
      notify("error", "Production status", error.message);
    } finally {
      setProductionLoading(false);
    }
  }, [api, notify]);

  const toggleProductionStatus = () => {
    const nextOpen = !productionOpen;
    setProductionOpen(nextOpen);
    if (nextOpen) loadProductionStatus();
  };

  return (
    <>
      <div className="section-title">
        <div>
          <span className="eyebrow">{t("Administrator controls")}</span>
          <h2>{t("Module Thresholds, Work Orders & Fleet Visibility")}</h2>
        </div>
        <div className="admin-title-actions">
          <button
            className={cls("settings-icon-btn", productionOpen && "active")}
            type="button"
            title="Settings"
            aria-label="Settings"
            onClick={toggleProductionStatus}
          >
            <Settings size={18} />
          </button>
        </div>
      </div>
      {productionOpen && (
        <>
          <AdminSettingsPanel themeMode={themeMode} setThemeMode={setThemeMode} language={language} setLanguage={setLanguage} />
          <ProductionStatusPanel
            status={productionStatus}
            loading={productionLoading}
            refresh={loadProductionStatus}
          />
        </>
      )}
      <div className="admin-grid">
        <form className="panel form-grid" onSubmit={submitWorkOrder}>
          <div className="panel-head full"><h3>{t("Assign Work")}</h3></div>
          <label>
            {t("Device")}
            <select name="device_id" value={workDeviceId} onChange={(e) => setWorkDeviceId(e.target.value)}>
              {devices.map((d) => <option key={d.id} value={d.id}>{d.display_name || d.machine_code}</option>)}
            </select>
          </label>
          <label>
            {t("Module")}
            <select name="module_id">
              <option value="">{t("All modules")}</option>
              {(workDevice?.modules || []).map((m) => <option key={m.id} value={m.id}>{m.module_name}</option>)}
            </select>
          </label>
          <label>
            {t("Assign To")}
            <select name="assigned_to">
              {users.map((u) => <option key={u.id} value={u.id}>{u.full_name || u.username}</option>)}
            </select>
          </label>
          <label>
            {t("Priority")}
            <select name="priority"><option>MEDIUM</option><option>HIGH</option><option>CRITICAL</option><option>LOW</option></select>
          </label>
          <label className="full">{t("Title")}<input name="title" placeholder="Inspect HT9046MX vacuum pump" required /></label>
          <label className="full">{t("Description")}<textarea name="description" rows="3" /></label>
          <p className="full muted">{t("Report an observed issue here even without a detector alert. Times below are Asia/Bangkok, not your browser timezone; leave blank if unknown.")}</p>
          <label>{t("Problem first observed")}<input type="datetime-local" name="event_started_at" /></label>
          <label>{t("Problem last observed (optional)")}<input type="datetime-local" name="event_ended_at" /></label>
          <label className="full">{t("Observed time precision")}<select name="event_time_precision"><option value="MINUTE">{t("MINUTE")}</option><option value="APPROXIMATE">{t("APPROXIMATE")}</option></select></label>
          <LoadingButton className="primary-btn full" busy={busy["work:create"]} busyText="Assigning" icon={Plus} type="submit">{t("Assign Work")}</LoadingButton>
        </form>
        <form className="panel form-grid" onSubmit={submitModuleStatus} key={statusModule?.id || "no-status-module"}>
          <div className="panel-head full"><h3>{t("Module Status")}</h3></div>
          <input type="hidden" name="module_id" value={statusModule?.id || ""} readOnly />
          <label>
            {t("Device")}
            <select value={statusDevice?.id || ""} onChange={(e) => setStatusDeviceId(e.target.value)}>
              {devices.map((d) => <option key={d.id} value={d.id}>{d.display_name || d.machine_code}</option>)}
            </select>
          </label>
          <label>
            {t("Module")}
            <select value={statusModule?.id || ""} onChange={(e) => setStatusModuleId(e.target.value)} disabled={!statusModules.length}>
              {statusModules.length ? statusModules.map((m) => <option key={m.id} value={m.id}>{m.module_name}</option>) : <option value="">No module</option>}
            </select>
          </label>
          <label className="full">
            {t("Status")}
            <select key={statusModule?.id || "none"} name="status" defaultValue={statusModule?.status === "WATCH" ? "WARNING" : statusModule?.status === "MONITORING" ? "NORMAL" : statusModule?.status || "NORMAL"} disabled={!statusModule}>
              {MODULE_STATUS_OPTIONS.map(([value, label]) => <option key={value} value={value}>{label}</option>)}
            </select>
          </label>
          <LoadingButton className="primary-btn full" busy={busy["module:status"]} busyText="Updating" icon={Save} type="submit" disabled={!statusModule}>
            {t("Update Module Status")}
          </LoadingButton>
        </form>
        <article className="panel numbering-panel">
          <div className="panel-head">
            <div>
              <h3>{t("Sequence & ID Numbering")}</h3>
              <p className="panel-note">{t("Reset Work Order # and Alert # back to 1")}</p>
            </div>
            <button
              className="ghost-btn icon-only"
              type="button"
              onClick={loadNumbering}
              disabled={numberingLoading}
              title={t("Refresh numbering status")}
              aria-label={t("Refresh numbering status")}
            >
              <RefreshCcw size={14} className={cls(numberingLoading && "spin")} />
            </button>
          </div>

          <div className="numbering-cards">
            <div className="numbering-card">
              <div className="numbering-card-header">
                <div className="numbering-card-title">
                  <Bell size={15} />
                  <strong>{t("Alert #")}</strong>
                </div>
                <span className="count-pill">Next: #{numbering?.alerts?.next_id ?? "—"}</span>
              </div>
              <div className="numbering-card-body">
                <div className="numbering-stat">
                  <span className="muted">{t("Total records")}</span>
                  <strong>{numbering?.alerts?.count ?? 0}</strong>
                </div>
                <div className="numbering-stat">
                  <span className="muted">{t("Current Max #")}</span>
                  <strong>#{numbering?.alerts?.max_id ?? 0}</strong>
                </div>
              </div>
              <LoadingButton
                className="danger-btn full"
                type="button"
                busy={resettingTarget === "alerts"}
                busyText={t("Resetting...")}
                icon={Trash2}
                onClick={() => handleResetNumbering("alerts")}
              >
                {t("Clear & Reset Alert #")}
              </LoadingButton>
            </div>

            <div className="numbering-card">
              <div className="numbering-card-header">
                <div className="numbering-card-title">
                  <Wrench size={15} />
                  <strong>{t("Work Order #")}</strong>
                </div>
                <span className="count-pill">Next: #{numbering?.work_orders?.next_id ?? "—"}</span>
              </div>
              <div className="numbering-card-body">
                <div className="numbering-stat">
                  <span className="muted">{t("Total records")}</span>
                  <strong>{numbering?.work_orders?.count ?? 0} ({numbering?.work_orders?.active ?? 0} active)</strong>
                </div>
                <div className="numbering-stat">
                  <span className="muted">{t("Current Max #")}</span>
                  <strong>#{numbering?.work_orders?.max_id ?? 0}</strong>
                </div>
              </div>
              <LoadingButton
                className="danger-btn full"
                type="button"
                busy={resettingTarget === "work_orders"}
                busyText={t("Resetting...")}
                icon={Trash2}
                onClick={() => handleResetNumbering("work_orders")}
              >
                {t("Clear & Reset Work Order #")}
              </LoadingButton>
            </div>

            <div className="numbering-all-actions">
              <LoadingButton
                className="ghost-btn full"
                style={{ color: "var(--red)" }}
                type="button"
                busy={resettingTarget === "all"}
                busyText={t("Resetting...")}
                icon={Trash2}
                onClick={() => handleResetNumbering("all")}
              >
                {t("Reset Both (#Alerts & #WorkOrders)")}
              </LoadingButton>
              <p className="panel-note" style={{ margin: "4px 0 0", fontSize: "10.5px", textAlign: "center" }}>
                {t("Historical maintenance service logs are preserved in audit.")}
              </p>
            </div>
          </div>
        </article>
      </div>
      <details className="panel detail-disclosure threshold-panel">
        <summary>
          <span>{t("Advanced Threshold Config")}</span>
          <span className="count-pill">{thresholdModule?.module_name || "No module"}</span>
        </summary>
        <p className="panel-note">{t("Optional per-module overrides for Vacuum Pump temperature, current and vibration. The approved Estimated Pressure safety rule always remains active. Compressor uses its ML Health Score.")}</p>
        <form className="form-grid embedded-form" onSubmit={submitThreshold} key={thresholdModule?.id || "no-module"}>
          <input type="hidden" name="module_id" value={thresholdModule?.id || ""} readOnly />
          <label>
            {t("Device")}
            <select value={thresholdDevice?.id || ""} onChange={(e) => setThresholdDeviceId(e.target.value)}>
              {devices.map((d) => <option key={d.id} value={d.id}>{d.display_name || d.machine_code}</option>)}
            </select>
          </label>
          <label>
            {t("Module")}
            <select value={thresholdModule?.id || ""} onChange={(e) => setThresholdModuleId(e.target.value)} disabled={!thresholdModules.length}>
              {groupedModules(thresholdDevice).map((group) => (
                <optgroup key={group.source} label={group.label}>
                  {group.modules.map((m) => <option key={m.id} value={m.id}>{m.module_name}</option>)}
                </optgroup>
              ))}
            </select>
          </label>
          {thresholdIsCompressor ? (
            <div className="full threshold-ml-note"><ShieldCheck size={18} /><span>{t("Compressor M1–M8 are evaluated by ML Health Score. Rule-based threshold overrides are not applied.")}</span></div>
          ) : thresholdModule ? (
            <>
              <label className="full threshold-toggle"><input name="advanced_enabled" type="checkbox" defaultChecked={thresholdEnabled} /><span><strong>{t("Enable advanced overrides")}</strong><small>{t("When off, validated default limits remain in effect.")}</small></span></label>
              <label>{t("Temp Warning (°C)")}<input name="temperature_warning" type="number" step="0.1" defaultValue={tv("temperature_c", "warning", 65)} required /></label>
              <label>{t("Temp Critical (°C)")}<input name="temperature_critical" type="number" step="0.1" defaultValue={tv("temperature_c", "critical", 80)} required /></label>
              <label>{t("Current Warning (A)")}<input name="current_warning" type="number" step="0.01" defaultValue={tv("current_a", "warning", 10)} required /></label>
              <label>{t("Current Critical (A)")}<input name="current_critical" type="number" step="0.01" defaultValue={tv("current_a", "critical", 15)} required /></label>
              <label>{t("Vibration Warning (G rms)")}<input name="vibration_warning" type="number" step="0.01" defaultValue={tv("vibration", "warning", 1.8)} required /></label>
              <label>{t("Vibration Critical (G rms)")}<input name="vibration_critical" type="number" step="0.01" defaultValue={tv("vibration", "critical", 2.8)} required /></label>
              <div className="full threshold-status"><StatusBadge value={thresholdModule.status || "OFFLINE"} /></div>
              <LoadingButton className="primary-btn full" busy={busy["threshold:save"]} busyText={t("Saving")} icon={Save} type="submit">{t("Save Threshold Config")}</LoadingButton>
            </>
          ) : <Empty>{t("No module available")}</Empty>}
        </form>
      </details>
      <article className="panel">
        <div className="panel-head">
          <h3>{t("Managed Handlers")}</h3>
          {editingDeviceId && <span className="unsaved-note">Edit mode: Save or Cancel before leaving this row.</span>}
        </div>
        <div className="table-wrap">
          <table className="data-table">
            <thead><tr><th>Device UID</th><th>Handler</th><th>Display</th><th>Location</th><th>Connection</th><th>Visibility</th><th>Status</th><th>Actions</th></tr></thead>
            <tbody>
              {devices.map((device) => {
                const editing = editingDeviceId === device.id;
                const isHidden = hiddenIds.includes(device.id) || hiddenIds.includes(device.machine_code) || hiddenIds.includes(device.device_uid);
                return (
                  <tr key={device.id}>
                    <td>{editing ? <input value={deviceDraft.device_uid} onChange={(e) => setDeviceDraft({ ...deviceDraft, device_uid: e.target.value })} /> : device.device_uid}</td>
                    <td>{editing ? <input value={deviceDraft.machine_code} onChange={(e) => setDeviceDraft({ ...deviceDraft, machine_code: e.target.value })} /> : device.machine_code}</td>
                    <td>{editing ? <input value={deviceDraft.display_name} onChange={(e) => setDeviceDraft({ ...deviceDraft, display_name: e.target.value })} /> : device.display_name}</td>
                    <td>{editing ? <input value={deviceDraft.location} onChange={(e) => setDeviceDraft({ ...deviceDraft, location: e.target.value })} /> : device.location || "-"}</td>
                    <td><ConnectionBadge state={device.connection_state} seconds={device.seconds_since_seen} /></td>
                    <td>
                      <button
                        type="button"
                        className={cls("ghost-btn", isHidden ? "danger-btn" : "")}
                        onClick={() => toggleHide && toggleHide(device)}
                        style={{ minHeight: "30px", padding: "4px 8px", fontSize: "12px", gap: "4px" }}
                        title={isHidden ? "Click to unhide from Handlers view" : "Click to hide from Handlers view"}
                      >
                        {isHidden ? <><Eye size={13} /> Hidden</> : <><EyeOff size={13} /> Visible</>}
                      </button>
                    </td>
                    <td><StatusBadge value={device.status} /></td>
                    <td>
                      <div className="table-actions">
                        {editing ? (
                          <>
                            <LoadingButton className="ghost-btn" busy={busy[`device:save:${device.id}`]} busyText="Saving" icon={Save} onClick={() => saveDevice(device.id)}>Save</LoadingButton>
                            <button className="ghost-btn" onClick={cancelEdit}><X size={15} />Cancel</button>
                          </>
                        ) : (
                          <>
                            <button className="ghost-btn" onClick={() => startEditDevice(device)}><Edit3 size={15} />Edit</button>
                            <LoadingButton className="danger-btn" busy={busy[`device:delete:${device.id}`]} busyText="Deleting" icon={Trash2} onClick={() => deleteDevice(device.id)}>Delete</LoadingButton>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </article>
    </>
  );
}

function AdminSettingsPanel({ themeMode, setThemeMode, language, setLanguage }) {
  const t = useT();
  return (
    <article className="panel admin-settings-panel">
      <div className="panel-head settings-panel-head">
        <div>
          <h3>{t("Interface Settings")}</h3>
          <p className="panel-note">{t("Dashboard appearance")}</p>
        </div>
      </div>
      <div className="theme-setting-row">
        <span className="theme-setting-icon" aria-hidden="true">
          {themeMode === "light" ? <Sun size={19} /> : <Moon size={19} />}
        </span>
        <div className="theme-setting-copy">
          <strong>{t("Color Theme")}</strong>
          <span>{t(themeMode === "light" ? "Light" : "Dark")}</span>
        </div>
        <div className="theme-segmented" role="group" aria-label="Color theme">
          <button
            className={cls(themeMode === "dark" && "active")}
            type="button"
            aria-pressed={themeMode === "dark"}
            onClick={() => setThemeMode("dark")}
          >
            <Moon size={16} />
            {t("Dark")}
          </button>
          <button
            className={cls(themeMode === "light" && "active")}
            type="button"
            aria-pressed={themeMode === "light"}
            onClick={() => setThemeMode("light")}
          >
            <Sun size={16} />
            {t("Light")}
          </button>
        </div>
      </div>
      <div className="theme-setting-row language-setting-row">
        <span className="theme-setting-icon" aria-hidden="true"><Languages size={19} /></span>
        <div className="theme-setting-copy">
          <strong>{t("Language")}</strong>
          <span>{t(language === "th" ? "Thai" : "English")}</span>
        </div>
        <div className="theme-segmented" role="group" aria-label={t("Language")}>
          <button className={cls(language === "en" && "active")} type="button" aria-pressed={language === "en"} onClick={() => setLanguage("en")}>ENG</button>
          <button className={cls(language === "th" && "active")} type="button" aria-pressed={language === "th"} onClick={() => setLanguage("th")}>TH</button>
        </div>
      </div>
    </article>
  );
}

function ProductionStatusPanel({ status, loading, refresh }) {
  const t = useT();
  const databaseState = status?.database || {};
  const telemetryState = status?.telemetry || {};
  const vacuumState = telemetryState.sources?.vacuum || {};
  const compressorState = telemetryState.sources?.compressor || {};
  const websocketState = status?.websocket || {};
  const ingestionState = status?.ingestion || {};
  const latestRecord = ingestionState.latest_record;
  const dbTone = databaseState.connected ? "good" : "danger";
  const wsTone = websocketState.loop_active ? "good" : "danger";
  const sourceTone = (source) => !telemetryState.enabled ? "neutral" : source.last_success_at ? "good" : "danger";
  const sourceValue = (source) => !source.configured ? "Not configured" : source.last_success_at ? "Reading" : "Unavailable";
  const pollTone = !telemetryState.enabled ? "neutral" : telemetryState.configured ? "good" : "danger";

  return (
    <article className="panel production-status-panel">
      <div className="panel-head">
        <div>
          <h3>{t("Production Status")}</h3>
          <p className="panel-note">{t("Runtime health for deployment checks and live troubleshooting.")}</p>
        </div>
        <LoadingButton className="ghost-btn" busy={loading} busyText="Refreshing" icon={RefreshCcw} onClick={refresh}>
          {t("Refresh")}
        </LoadingButton>
      </div>
      {!status && loading ? (
        <Empty>{t("Loading production status")}</Empty>
      ) : (
        <div className="production-status-grid">
          <ProductionStatusCard
            icon={Database}
            title="MySQL"
            value={databaseState.connected ? "Connected" : "Offline"}
            tone={dbTone}
            rows={[
              ["Database", databaseState.database_name || "-"],
              ["Host", `${databaseState.host || "-"}:${databaseState.port || "-"}`],
              ["Server time", dateText(databaseState.server_time)],
              ["Error", databaseState.error || databaseState.startup_error || "-"],
            ]}
          />
          <ProductionStatusCard
            icon={Activity}
            title="Vacuum Pump source"
            value={sourceValue(vacuumState)}
            tone={sourceTone(vacuumState)}
            rows={[
              ["Source", `${vacuumState.schema || "-"}.${vacuumState.table || "-"}`],
              ["Host", `${telemetryState.host || "-"}:${telemetryState.port || "-"}`],
              ["Last read", vacuumState.last_success_at ? dateText(vacuumState.last_success_at) : "-"],
              ["Error", vacuumState.error || "-"],
            ]}
          />
          <ProductionStatusCard
            icon={Server}
            title="Compressor source"
            value={sourceValue(compressorState)}
            tone={sourceTone(compressorState)}
            rows={[
              ["Source", `${compressorState.schema || "-"}.${compressorState.table || "-"}`],
              ["Host", `${telemetryState.host || "-"}:${telemetryState.port || "-"}`],
              ["Last read", compressorState.last_success_at ? dateText(compressorState.last_success_at) : "-"],
              ["Error", compressorState.error || "-"],
            ]}
          />
          <ProductionStatusCard
            icon={RefreshCcw}
            title="Live polling"
            value={telemetryState.enabled ? telemetryState.configured ? "Active" : "Needs credentials" : "Disabled"}
            tone={pollTone}
            rows={[
              ["Every", `${formatCell(telemetryState.poll_interval_seconds || 0)} ${t("seconds")}`],
              ["Last poll", telemetryState.last_poll_at ? dateText(telemetryState.last_poll_at) : "-"],
              ["Live modules", formatCell(ingestionState.live_source_samples || 0)],
              ["Polls", formatCell(ingestionState.poll_count || 0)],
              ["Latest", latestRecord ? `${latestRecord.machine_code || latestRecord.display_name} / ${latestRecord.module_name}` : "-"],
            ]}
          />
          <ProductionStatusCard
            icon={Bell}
            title="WebSocket"
            value={`${formatCell(websocketState.active_connections || 0)} ${t("clients")}`}
            tone={wsTone}
            rows={[
              ["Loop", websocketState.loop_active ? "Active" : "Not ready"],
              ["Broadcasts", formatCell(websocketState.broadcast_count || 0)],
              ["Last broadcast", websocketState.last_broadcast_at ? dateText(websocketState.last_broadcast_at) : "-"],
              ["Error", websocketState.last_error || "-"],
            ]}
          />
        </div>
      )}
    </article>
  );
}

function ProductionStatusCard({ icon: Icon, title, value, tone, rows }) {
  const t = useT();
  return (
    <section className={cls("production-status-card", tone)}>
      <div className="production-status-card-head">
        <span><Icon size={17} />{t(title)}</span>
        <b>{t(value)}</b>
      </div>
      <dl>
        {rows.map(([label, rowValue]) => (
          <div key={label}>
            <dt>{t(label)}</dt>
            <dd>{rowValue}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function Detail({ device, module, setModuleId, close, history, telemetry, alerts, logs, timeRange, setTimeRange }) {
  const t = useT();
  const detailRef = useRef(null);
  const compressorModule = moduleSource(module) === "compressor";
  const sourceGroups = useMemo(() => groupedModules(device), [device]);
  const selectedSource = moduleSource(module);
  const selectedGroup = sourceGroups.find((group) => group.source === selectedSource) || sourceGroups[0];
  const sensorGauges = useMemo(() => compressorModule ? [] : vacuumSensorGaugeItems(module), [compressorModule, module]);
  const compressorHealthAvailable = compressorModule
    && module.health_score !== null
    && module.health_score !== undefined
    && Number.isFinite(Number(module.health_score));
  const vacuumState = !compressorModule ? vacuumPressureState(module.pressure_kpa) : null;

  const moduleAlerts = alerts.filter((a) => a.module_id === module.id).slice(0, 6);
  const moduleLogs = logs.filter((log) => log.module_id === module.id).slice(0, 6);
  const [relationship, setRelationship] = useState({ x: "valve", y: "lp_2nd" });
  const currentKey = `${device.id}:${module.id}:${timeRange}`;
  const currentTelemetry = telemetry.key === currentKey ? telemetry : { loading: true, error: "" };
  // The API applies current-time bounds. Never shift an empty recent range to old readings.
  const filteredHistory = telemetry.key === currentKey ? history : EMPTY_HISTORY;
  const filteredMetricRows = filteredHistory;
  const chartUnavailable = currentTelemetry.loading || !filteredHistory.length;
  const chartFeedback = !currentTelemetry.loading && !filteredHistory.length ? (
    currentTelemetry.error ? <p role="alert">{t("Could not load chart data")}: {currentTelemetry.error}</p> : <div className="handler-chart-empty">
      <p>{t("No telemetry in the selected range")}</p>
      {timeRange !== "All" && <button className="ghost-btn" onClick={() => setTimeRange("All")}>{t("Show latest history")}</button>}
      <small>{t("Last sensor reading")}: {dateText(module.diagnostic_at)}</small>
    </div>
  ) : null;
  const plottedCompressorRows = useMemo(() => compressorModule ? dynamicMetricRows(filteredHistory) : EMPTY_HISTORY, [compressorModule, filteredHistory]);
  const correlationData = useMemo(() => compressorModule ? historyCorrelation(plottedCompressorRows) : null, [compressorModule, plottedCompressorRows]);
  const relationshipData = useMemo(() => compressorModule ? historyRelationship(plottedCompressorRows, relationship.x, relationship.y) : null, [compressorModule, plottedCompressorRows, relationship.x, relationship.y]);
  const thresholdSignature = JSON.stringify(module.thresholds);
  const vacuumCharts = useMemo(() => compressorModule ? null : ({
    overview: overviewTrend(filteredHistory, module.thresholds),
    thermal: thermalTrend(filteredHistory, module.thresholds),
    current: singleTrend(filteredHistory, "current_a", "Current A", COLOR_WARN, module.thresholds, "current_a"),
    vibration: vibrationTrend(filteredHistory, module.thresholds),
  }), [compressorModule, filteredHistory, thresholdSignature]);

  useEffect(() => {
    detailRef.current?.scrollTo({ top: 0, left: 0 });
  }, [device.id]);

  return (
    <section className="detail-view" ref={detailRef}>
      <div className="detail-topbar">
        <button className="ghost-btn" onClick={close}><ArrowLeft size={16} />{t("Back")}</button>
        <div>
          <span className="eyebrow">{t("Handler Detail")}</span>
          <h2>{machineTitle(device)}</h2>
        </div>
        <ConnectionBadge state={device.connection_state} seconds={device.seconds_since_seen} />
        <div className="filter-tabs compact">
          {["All", "1h", "6h", "24h", "7d"].map((r) => (
            <button key={r} className={timeRange === r ? "active" : ""} onClick={() => setTimeRange(r)}>{r === "All" ? t("Latest history") : r}</button>
          ))}
        </div>
      </div>
      {!currentTelemetry.loading && currentTelemetry.error && filteredHistory.length > 0 && <p className="panel-note" role="alert">{t("Could not load chart data")}: {currentTelemetry.error}</p>}
      <div className="handler-module-tabs" aria-label="Handler modules">
        {sourceGroups.map((group) => (
          <button
            key={group.source}
            className={group.source === selectedGroup?.source ? "active" : ""}
            onClick={() => setModuleId((activeModules({ modules: group.modules })[0] || group.modules[0]).id)}
          >
            {group.label}
            <small>{group.modules.length} {t("modules")}</small>
          </button>
        ))}
      </div>
      {selectedGroup?.source === "compressor" && (
        <div className="module-tabs compressor-module-tabs" aria-label="Compressor modules">
          {selectedGroup.modules.map((m) => (
            <button key={m.id} className={m.id === module.id ? "active" : ""} onClick={() => setModuleId(m.id)}>
              {m.module_name.replace("Compressor ", "")}
              {m.source_status && <small>{m.source_status}</small>}
            </button>
          ))}
        </div>
      )}
      <div className="sensor-card-grid detail-sensor-card-grid">
        {compressorModule ? compressorPrimaryMetrics(module).map((item) => (
          <SensorTrendCard
            key={item.key}
            icon={item.icon}
            label={item.label}
            value={item.value}
            unit={item.unit}
            range={item.range}
            color={item.color}
              option={filteredHistory.length ? metricSparklineOption(dynamicMetricRows(filteredMetricRows), item.key, item.color, item.unit, item.label) : null}
          />
        )) : sensorGauges.map((gauge) => {
          const sensorConfig = {
            pressure: { icon: Activity, value: n(module.pressure_kpa, 2), range: "Normal -90 to -70 kPa", dataKey: "pressure_kpa" },
            temperature: { icon: Thermometer, value: n(module.temperature_c, 1), range: "-20 - 120 C", dataKey: "temperature_c" },
            vibration: { icon: Activity, value: n(module.vibration, 2), range: "Calibration signal", dataKey: "vibration" },
            current: { icon: Zap, value: n(module.current_a, 2), range: "0 - 20 A", dataKey: "current_a" },
          }[gauge.key];
          const color = gauge.tone === "danger" ? COLOR_DANGER : gauge.tone === "warn" ? COLOR_WARN : gauge.tone === "offline" ? COLOR_OFFLINE : COLOR_BLUE;
          return (
            <SensorTrendCard
              key={gauge.key}
              icon={sensorConfig.icon}
              label={t(gauge.label)}
              value={sensorConfig.value}
              unit={gauge.unit}
              range={sensorConfig.range}
              color={color}
              option={filteredHistory.length ? metricSparklineOption(filteredHistory, sensorConfig.dataKey, color, gauge.unit, gauge.label) : null}
            />
          );
        })}
      </div>
      <div className="detail-grid" aria-busy={currentTelemetry.loading}>
        <article className="panel condition-panel">
          <div className="panel-head"><h3>{t(compressorModule ? "ML Condition" : "Vacuum Rule Status")}</h3><StatusBadge value={compressorModule && !compressorHealthAvailable && !module.operation_pull_enabled ? "AWAITING_ML_SCORE" : module.status} /></div>
          {compressorModule ? (
            module.operation_pull_enabled ? (
              <div className="context-condition-body">
                <div><span className="eyebrow">{module.operation_result_fresh === false ? t("No recent Operation result") : module.operation_mode === "DETECTOR_LIVE" ? t("Frozen Active Context") : t("Shadow evidence · not voting")}</span>
                <strong>{t(conditionLabel(module.status))}</strong>
                <p>{t(module.ai_condition || "Awaiting Operation result")}</p>
                {module.operation_evidence && <p>{module.operation_evidence.feature}: {n(module.operation_evidence.delta, 2)} {module.operation_evidence.unit}</p>}
                <small>{t("Result at")}: {dateText(module.health_score_at)}</small>
                <p className="calibration-note">{t("No synthetic Health Score; unsupported states are not evaluated.")}</p></div>
              </div>
            ) : compressorHealthAvailable ? (
              <div className="condition-body">
                <ScoreRing score={module.health_score} />
                <div>
                  <span className="eyebrow">{t("Latest imported ML result")}</span>
                  <div className="score-block"><strong>{n(module.health_score, 0)}</strong><span>{t("Health Score")}</span></div>
                  <p className="ai-box">{module.ai_condition || t("Condition not supplied")} / {module.ai_model_version || t("Version not supplied")}</p>
                  {String(module.ai_model_version || "").includes("MOCK_ONLY") && <p className="ai-box">{t("TEST DATA — not an approved active profile")}</p>}
                  <small>{t("ML result at")}: {dateText(module.health_score_at)}</small>
                </div>
              </div>
            ) : (
              <div className="condition-empty">
                <span className="condition-empty-icon"><RefreshCcw size={22} /></span>
                <div><strong>{t("Awaiting ML Score")}</strong><p>{t("No row has been received from compressor_health_scores for this machine and module.")}</p></div>
              </div>
            )
          ) : (
            <div className="vacuum-rule-summary">
              <div className={cls("vacuum-state-mark", vacuumState.tone)}><Activity size={22} /><strong>{t(vacuumState.label)}</strong></div>
              <div className="vacuum-pressure-value"><span>{t("Estimated Pressure")}</span><strong>{n(module.pressure_kpa, 1)} <em>kPa</em></strong></div>
              <div className="vacuum-rule-bands">
                <span><i className="good" />{t("Normal −90 to −70")}</span>
                <span><i className="warn" />{t("Warning below −90 or above −70 to −60")}</span>
                <span><i className="danger" />{t("Critical above −60")}</span>
              </div>
              <p className="calibration-note">{t("Estimated from vibration: V = −0.0439P − 2.2098 (R² 0.9764). This is not a pressure-sensor measurement.")}</p>
            </div>
          )}
        </article>
        <article className="panel metrics-panel">
          <div className="panel-head">
            <h3>{t("Sensor Snapshot")}</h3>
            <span className="count-pill">{t("Latest")}</span>
          </div>
          {!compressorModule && <div className="sensor-gauge-grid">
            {sensorGauges.map((item) => <SensorGauge key={item.key} {...item} />)}
          </div>}
          <div className="source-snapshot-grid">
            {compressorModule ? <>
              <MiniMetric label="Busy" value={busyLabel(module.metrics?.busy?.[0] ?? module.metrics?.busy ?? module.source_busy ?? module.busy)} />
              <MiniMetric label="Status" value={module.operating_status || module.source_status || module.status || "Run"} />
              <MiniMetric label="SV" value={module.set_valve_status || module.source_sv || module.sv || "Off"} />
            </> : ACCEL_SNAPSHOT_KEYS.map((key) => (
              <MiniMetric key={key} label={sourceMetricLabel(key)} value={accelSnapshotValue(module, key) ?? t("No data")} />
            ))}
          </div>
        </article>
        {compressorModule ? (
          <>
            <TrendPanel
              className="full-span featured-trend"
              unavailable={chartUnavailable}
              feedback={chartFeedback}
              title="Stage Pressure Profile (HP1, LP1, HP2, LP2)"
              note="High- and low-side pressure through both compressor stages over time"
              option={dynamicMetricTrend(filteredMetricRows, [
                { key: "hp_1st", label: "HP 1st" },
                { key: "lp_1st", label: "LP 1st" },
                { key: "hp_2nd", label: "HP 2nd" },
                { key: "lp_2nd", label: "LP 2nd" },
              ], "Pressure", true, module)}
            />
            <TrendInsight title="HP2 Trend Summary" rows={dynamicMetricRows(filteredMetricRows)} metric="hp_2nd" unit="source units" method={module.operation_pull_enabled ? "Frozen Context assessment" : "ML Health Score"} />
            <TrendPanel
              unavailable={chartUnavailable}
              title="Thermal Operating Band (Temp Hi & Temp Lo)"
              note="Temperature readings across high and low sides"
              option={dynamicMetricTrend(filteredMetricRows, [
                { key: "temperature_hi", label: "Temp High" },
                { key: "temperature_lo", label: "Temp Low" },
              ], "Temperature °C", true, module)}
            />
            <TrendPanel
              unavailable={chartUnavailable}
              title="Valve Position Activity"
              note="Valve opening level over time"
              option={dynamicMetricTrend(filteredMetricRows, [
                { key: "valve", label: "Valve Position", area: true },
              ], "Valve", true, module)}
            />
            <TrendPanel
              unavailable={chartUnavailable}
              title="Stage 1 Compression: HP1 vs LP1"
              note="Primary stage intake and discharge pressure differential"
              option={dynamicMetricTrend(filteredMetricRows, [
                { key: "hp_1st", label: "HP 1st Stage" },
                { key: "lp_1st", label: "LP 1st Stage" },
              ], "Stage 1 Pressure", true, module)}
            />
            <TrendPanel
              unavailable={chartUnavailable}
              title="Stage 2 Compression: HP2 vs LP2"
              note="Secondary stage boost differential pressure"
              option={dynamicMetricTrend(filteredMetricRows, [
                { key: "hp_2nd", label: "HP 2nd Stage" },
                { key: "lp_2nd", label: "LP 2nd Stage" },
              ], "Stage 2 Pressure", true, module)}
            />
            <TrendPanel
              unavailable={chartUnavailable}
              title="SV & Busy States"
              note="Observed control states: 1 = ON, 0 = OFF; gaps = unknown"
              option={controlStateOption(dynamicMetricRows(filteredMetricRows))}
            />
            <CorrelationPanel data={correlationData} unavailable={chartUnavailable} />
            <RelationshipPanel data={relationshipData} unavailable={chartUnavailable} relationship={relationship} setRelationship={setRelationship} />
          </>
        ) : (
          <>
            <TrendPanel
              className="full-span featured-trend"
              unavailable={chartUnavailable}
              feedback={chartFeedback}
              title="Vacuum Pump Operating Overview"
              note="Motor current, vibration, and estimated pressure over time"
              option={vacuumCharts.overview}
            />
            <TrendPanel unavailable={chartUnavailable} title="Estimated Pressure" note="Pressure is calculated from vibration; no pressure sensor is installed" option={vacuumCharts.thermal} />
            <TrendPanel unavailable={chartUnavailable} title="Motor Current" note="Electrical load and operating stability" option={vacuumCharts.current} />
            <TrendPanel unavailable={chartUnavailable} className="full-span" title="Vibration & 3-Axis Acceleration" note="Mechanical vibration with X, Y, and Z acceleration" option={vacuumCharts.vibration} />
          </>
        )}
        <details className="panel detail-disclosure">
          <summary><span>{t("Recent Alerts")}</span><span className="count-pill">{moduleAlerts.length}</span></summary>
          <CompactList rows={moduleAlerts} render={(a) => <><strong>{a.title}</strong><span>{dateText(a.recorded_at)} / {a.severity}</span><p>{a.message}</p></>} empty={t("No recent alerts")} />
        </details>
        <details className="panel detail-disclosure">
          <summary><span>{t("Service History")}</span><span className="count-pill">{moduleLogs.length}</span></summary>
          <CompactList rows={moduleLogs} render={(log) => <><strong>{log.technician_name}</strong><span>{dateText(log.recorded_at)}</span><p>{log.action_taken}</p></>} empty={t("No service logs")} />
        </details>
      </div>
    </section>
  );
}

function TrendInsight({ title, rows, metric, unit, method }) {
  const t = useT();
  const values = rows.map((row) => sensorNumber(row[metric])).filter(Number.isFinite);
  const current = values.at(-1);
  const first = values[0];
  const delta = Number.isFinite(current) && Number.isFinite(first) ? current - first : null;
  const direction = delta === null ? "No data" : Math.abs(delta) < 0.01 ? "Stable" : delta > 0 ? "Increasing" : "Decreasing";
  return <article className="panel trend-insight"><span className="eyebrow">{t("Evidence summary")}</span><h3>{t(title)}</h3><div className="trend-insight-values"><div><small>{t("Current")}</small><strong>{Number.isFinite(current) ? n(current, 1) : "--"}</strong><span>{unit}</span></div><div><small>{t("Window change")}</small><strong className={delta > 0 ? "trend-up" : delta < 0 ? "trend-down" : ""}>{delta === null ? "--" : `${delta > 0 ? "+" : ""}${n(delta, 1)}`}</strong><span>{t(direction)}</span></div><div><small>{t("Condition method")}</small><strong>{t(method)}</strong><span>{t("No rule threshold")}</span></div></div></article>;
}

function CorrelationPanel({ data, unavailable }) {
  const option = useMemo(() => correlationOption(data), [data]);
  return <article className="panel analytics-panel"><div className="panel-head"><div><h3>Signal Relationships</h3><p>Correlation within the selected operating window</p></div><span className="count-pill">{data?.samples ?? 0} samples</span></div><HandlerChart option={option} unavailable={unavailable} className="chart analytics-chart" /></article>;
}

function RelationshipPanel({ data, relationship, setRelationship, unavailable }) {
  const option = useMemo(() => relationshipOption(data), [data]);
  const signals = ["valve", "hp_1st", "lp_1st", "hp_2nd", "lp_2nd", "temperature_hi", "temperature_lo"];
  return <article className="panel analytics-panel"><div className="panel-head"><div><h3>Relationship Explorer</h3><p>Paired samples only; this is evidence, not a fault conclusion.</p></div><span className="count-pill">r {data?.correlation ?? "--"}</span></div><div className="relationship-controls"><label>X signal<select value={relationship.x} onChange={(event) => setRelationship({ ...relationship, x: event.target.value })}>{signals.map((signal) => <option key={signal} value={signal}>{sourceMetricLabel(signal)}</option>)}</select></label><label>Y signal<select value={relationship.y} onChange={(event) => setRelationship({ ...relationship, y: event.target.value })}>{signals.map((signal) => <option key={signal} value={signal}>{sourceMetricLabel(signal)}</option>)}</select></label></div><HandlerChart option={option} unavailable={unavailable} className="chart analytics-chart" /></article>;
}

function correlationOption(data) {
  if (!data?.signals?.length) return emptyChartOption("No paired compressor telemetry in this time range");
  const cells = data.matrix.flatMap((row, y) => row.map((value, x) => [x, y, value]));
  return {
    backgroundColor: "transparent", tooltip: { position: "top", formatter: (item) => `${sourceMetricLabel(data.signals[item.value[0]])} × ${sourceMetricLabel(data.signals[item.value[1]])}<br/>Pearson r: <b>${item.value[2] ?? "--"}</b>` },
    grid: { left: 105, right: 42, top: 15, bottom: 82 },
    xAxis: { type: "category", data: data.signals.map(sourceMetricLabel), axisLabel: { color: CHART_AXIS, rotate: 35 }, axisLine: { lineStyle: { color: CHART_GRID } } },
    yAxis: { type: "category", data: data.signals.map(sourceMetricLabel), axisLabel: { color: CHART_AXIS }, axisLine: { lineStyle: { color: CHART_GRID } } },
    visualMap: { min: -1, max: 1, calculable: false, orient: "horizontal", left: "center", bottom: 6, textStyle: { color: CHART_AXIS }, inRange: { color: [COLOR_BLUE, "#15181a", COLOR_DANGER] } },
    series: [{ type: "heatmap", data: cells, label: { show: true, color: "#f1f3f4", formatter: (item) => item.value[2] == null ? "--" : item.value[2].toFixed(2) }, itemStyle: { borderColor: "#2a3034", borderWidth: 2 } }],
  };
}

function relationshipOption(data) {
  if (!data?.points?.length) return emptyChartOption("No paired samples for this relationship");
  return {
    backgroundColor: "transparent", tooltip: { trigger: "item", formatter: (item) => `${data.x_signal}: <b>${n(item.value[0], 2)}</b><br/>${data.y_signal}: <b>${n(item.value[1], 2)}</b><br/><small>${dateText(item.data[2])}</small>` },
    grid: { left: 60, right: 24, top: 24, bottom: 48 },
    xAxis: { type: "value", name: sourceMetricLabel(data.x_signal), nameTextStyle: { color: CHART_AXIS }, axisLabel: { color: CHART_AXIS }, splitLine: { lineStyle: { color: CHART_GRID, type: "dashed" } } },
    yAxis: { type: "value", name: sourceMetricLabel(data.y_signal), nameTextStyle: { color: CHART_AXIS }, axisLabel: { color: CHART_AXIS }, splitLine: { lineStyle: { color: CHART_GRID, type: "dashed" } } },
    series: [{ type: "scatter", data: data.points.map((point) => [point.x, point.y, point.recorded_at]), symbolSize: 7, itemStyle: { color: COLOR_TEAL, opacity: 0.7 } }],
  };
}

function emptyChartOption(message) {
  return { backgroundColor: "transparent", xAxis: { show: false }, yAxis: { show: false }, series: [], graphic: [{ type: "text", left: "center", top: "middle", style: { text: message, fill: CHART_AXIS, fontSize: 13 } }] };
}

function HandlerChart({ option, className = "chart", unavailable, feedback }) {
  return unavailable ? <div className={cls(className, "handler-chart-placeholder")}>{feedback}</div> : <EChart option={option} className={className} />;
}

function TrendPanel({ title, note, option, className, unavailable, feedback }) {
  const t = useT();
  return (
    <article className={cls("panel", "equipment-trend-panel", className)}>
      <div className="panel-head equipment-chart-head">
        <div>
          <h3>{t(title)}</h3>
          <p>{t(note)}</p>
        </div>
        <span className="chart-interaction-hint">{t("Scroll to zoom · drag to inspect")}</span>
      </div>
      <HandlerChart option={option} unavailable={unavailable} feedback={feedback} className={cls("chart", className?.includes("featured-trend") && "large")} />
    </article>
  );
}

function compressorPrimaryMetrics(module) {
  const metrics = module?.metrics || {};
  const toneColor = statusColor(module?.status || "NORMAL");
  return [
    { key: "hp_1st", label: "HP1", value: n(metrics.hp_1st, 1), unit: "", range: compressorRange(module, "hp_1st", "Stage 1 High Pressure"), color: toneColor, icon: Activity },
    { key: "lp_1st", label: "LP1", value: n(metrics.lp_1st, 1), unit: "", range: compressorRange(module, "lp_1st", "Stage 1 Low Pressure"), color: toneColor, icon: Activity },
    { key: "hp_2nd", label: "HP2", value: n(metrics.hp_2nd, 1), unit: "", range: compressorRange(module, "hp_2nd", "Stage 2 High Pressure"), color: toneColor, icon: Activity },
    { key: "lp_2nd", label: "LP2", value: n(metrics.lp_2nd, 1), unit: "", range: compressorRange(module, "lp_2nd", "Stage 2 Low Pressure"), color: toneColor, icon: Activity },
    { key: "temperature_hi", label: "Temp Hi", value: n(metrics.temperature_hi, 1), unit: "°C", range: compressorRange(module, "temperature_hi", "High Temperature"), color: toneColor, icon: Thermometer },
    { key: "temperature_lo", label: "Temp Lo", value: n(metrics.temperature_lo, 1), unit: "°C", range: compressorRange(module, "temperature_lo", "Low Temperature"), color: toneColor, icon: Thermometer },
    { key: "valve", label: "Valve", value: n(metrics.valve, 0), unit: "", range: compressorRange(module, "valve", "Valve Position"), color: toneColor, icon: Zap },
  ];
}

function compressorRange(module, metric, fallback) {
  return fallback;
}

const metricTimelineCache = new WeakMap();
function dynamicMetricRows(metricRows) {
  if (metricTimelineCache.has(metricRows)) return metricTimelineCache.get(metricRows);
  const timeline = new Map();
  metricRows.forEach(row => {
    const stamp = row.recorded_at;
    if (!stamp) return;
    if (!timeline.has(stamp)) timeline.set(stamp, { recorded_at: stamp });
    if (row.metric_key) timeline.get(stamp)[row.metric_key] = sensorNumber(row.metric_value);
    else Object.assign(timeline.get(stamp), row);
  });
  const rows = [...timeline.values()].sort((a, b) => new Date(a.recorded_at) - new Date(b.recorded_at));
  metricTimelineCache.set(metricRows, rows);
  return rows;
}

const metricTrendCache = new WeakMap();
function dynamicMetricTrend(metricRows, definitions, yAxisName, interactive = true, module = null) {
  let options = metricTrendCache.get(metricRows);
  if (!options) { options = new Map(); metricTrendCache.set(metricRows, options); }
  const key = JSON.stringify([definitions, yAxisName, interactive, module?.status]);
  if (!options.has(key)) options.set(key, buildDynamicMetricTrend(metricRows, definitions, yAxisName, interactive, module));
  return options.get(key);
}

function buildDynamicMetricTrend(metricRows, definitions, yAxisName, interactive = true, module = null) {
  const rows = dynamicMetricRows(metricRows);
  const labels = rows.map((row) => new Date(row.recorded_at).toLocaleTimeString());
  const visibleDefinitions = definitions.filter((definition) => rows.some((row) => Number.isFinite(row[definition.key])));
  const toneColor = statusColor(module?.status || "NORMAL");
  const harmonicColors = [toneColor, COLOR_BLUE, "#818cf8", toneColor === COLOR_TEAL ? "#34d399" : COLOR_TEAL];

  if (!interactive) {
    return {
      backgroundColor: "transparent",
      animationDuration: 500,
      grid: { left: 0, right: 0, top: 8, bottom: 0 },
      xAxis: { type: "category", data: labels, show: false, boundaryGap: false },
      yAxis: { type: "value", show: false, scale: true },
      series: visibleDefinitions.map((definition) => ({
        name: definition.label,
        type: "line",
        data: rows.map((row) => row[definition.key]),
        showSymbol: false,
        smooth: 0.3,
        connectNulls: false,
        lineStyle: { width: 2, color: toneColor },
        areaStyle: { color: toneColor, opacity: 0.08 },
      })),
    };
  }

  return {
    backgroundColor: "transparent",
    animation: false,
    color: visibleDefinitions.map((definition, idx) => PRESSURE_COLORS[definition.key] || harmonicColors[idx % harmonicColors.length]),
    tooltip: {
      trigger: "axis",
      confine: true,
      transitionDuration: 0.1,
      axisPointer: {
        type: "cross",
        lineStyle: { color: CHART_AXIS, type: "dashed", width: 1.5 },
        label: { backgroundColor: "#273744", precision: 2 },
      },
      formatter: (params) => {
        if (!params || !params.length) return "";
        const time = params[0].axisValueLabel || params[0].name;
        let res = `<div style="font-weight:600;margin-bottom:4px;opacity:0.75">${time}</div>`;
        params.forEach((p) => {
          const val = Number.isFinite(p.value) ? n(p.value, 2) : "--";
          res += `<div style="display:flex;align-items:center;justify-content:space-between;gap:14px;font-size:12px">
            <span style="display:flex;align-items:center;gap:6px">
              <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${p.color};flex-shrink:0"></span>
              <span style="opacity:0.85">${p.seriesName}</span>
            </span>
            <strong style="margin-left:8px;font-weight:700">${val}</strong>
          </div>`;
        });
        return res;
      },
    },
    legend: { top: 2, left: 8, itemWidth: 18, itemHeight: 3, textStyle: { color: CHART_AXIS } },
    grid: { left: 62, right: 28, top: 52, bottom: 66 },
    dataZoom: [
      { type: "inside", start: rows.length > 150 ? 50 : 0, end: 100, zoomOnMouseWheel: true, moveOnMouseMove: true },
      { type: "slider", start: rows.length > 150 ? 50 : 0, end: 100, height: 18, bottom: 12, borderColor: CHART_GRID, fillerColor: "rgba(79, 150, 209, 0.16)", handleStyle: { color: COLOR_BLUE } },
    ],
    xAxis: {
      type: "category",
      data: labels,
      boundaryGap: false,
      axisLabel: { color: CHART_AXIS, hideOverlap: true },
      axisLine: { lineStyle: { color: CHART_GRID } },
    },
    yAxis: {
      type: "value",
      name: yAxisName,
      scale: true,
      nameTextStyle: { color: CHART_AXIS, padding: [0, 0, 6, 0] },
      axisLabel: { color: CHART_AXIS },
      splitLine: { lineStyle: { color: CHART_GRID, type: "dashed", opacity: 0.75 } },
    },
    series: visibleDefinitions.map((definition, index) => {
      const seriesColor = PRESSURE_COLORS[definition.key] || harmonicColors[index % harmonicColors.length];
      return {
        name: definition.label,
        type: "line",
        data: rows.map((row) => row[definition.key]),
        showSymbol: rows.length < 25,
        symbol: "circle",
        symbolSize: 5,
        smooth: definition.step ? false : 0.25,
        step: definition.step,
        connectNulls: false,
        lineStyle: { width: index === 0 ? 2.5 : 2.0, color: seriesColor, type: definition.key.startsWith("lp_") ? "dashed" : "solid" },
        itemStyle: { color: seriesColor },
        areaStyle: definition.area ? { color: seriesColor, opacity: 0.12 } : undefined,
        emphasis: { focus: "series", lineStyle: { width: 3.5 } },
      };
    }),
    graphic: visibleDefinitions.length ? [] : [{ type: "text", left: "center", top: "middle", style: { text: "No telemetry in this time range", fill: CHART_AXIS, fontSize: 13 } }],
  };
}

function SensorGauge({ label, value, unit, percent, tone, note }) {
  return (
    <div className={cls("sensor-gauge", tone)}>
      <div className="sensor-gauge-top">
        <span>{label}</span>
        <strong>{value}</strong>
      </div>
      <div className="sensor-track">
        <i style={{ width: `${clamp(percent, 0, 100)}%` }} />
      </div>
      <div className="sensor-gauge-foot">
        <span>{note}</span>
        <b>{unit}</b>
      </div>
    </div>
  );
}

function vacuumPressureState(rawPressure) {
  const pressure = Number(rawPressure);
  if (!Number.isFinite(pressure)) return { label: "NO DATA", tone: "offline" };
  if (pressure > -60) return { label: "CRITICAL", tone: "danger" };
  if (pressure > -70 || pressure < -90) return { label: "WARNING", tone: "warn" };
  return { label: "NORMAL", tone: "good" };
}

function vacuumSensorGaugeItems(module) {
  const thresholds = module.thresholds || {};
  return [
    upperGauge("temperature", "Temperature", module.temperature_c, "C", thresholds.temperature_c?.warning ?? 65, thresholds.temperature_c?.critical ?? 80, 1),
    vacuumPressureGauge(module.pressure_kpa),
    upperGauge("current", "Current", module.current_a, "A", thresholds.current_a?.warning ?? 10, thresholds.current_a?.critical ?? 15, 2),
    vacuumVibrationGauge(module.vibration, module.pressure_kpa),
  ];
}

function vacuumPressureGauge(rawValue) {
  const value = Number(rawValue);
  const valid = Number.isFinite(value);
  const state = vacuumPressureState(value);
  return {
    key: "pressure",
    label: "Estimated Pressure",
    unit: "kPa",
    value: valid ? n(value, 1) : "--",
    percent: valid ? ((value + 110) / 110) * 100 : 0,
    tone: state.tone,
    note: "Normal −90 to −70 · estimated",
  };
}

function vacuumVibrationGauge(rawValue, rawPressure) {
  const value = Number(rawValue);
  const valid = Number.isFinite(value);
  const state = vacuumPressureState(rawPressure);
  return {
    key: "vibration",
    label: "Vibration",
    unit: "G rms",
    value: valid ? n(value, 2) : "--",
    percent: valid ? (value / 2.2) * 100 : 0,
    tone: valid ? state.tone : "offline",
    note: "Input to pressure estimate",
  };
}

function upperGauge(key, label, rawValue, unit, warning, critical, digits) {
  const value = Number(rawValue);
  const valid = Number.isFinite(value);
  const tone = !valid ? "offline" : value >= critical ? "danger" : value >= warning ? "warn" : "good";
  return {
    key,
    label,
    unit,
    value: valid ? n(value, digits) : "--",
    percent: valid ? (value / Math.max(critical, 1)) * 100 : 0,
    tone,
    note: `Warn ${n(warning, digits)} / Crit ${n(critical, digits)}`,
  };
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, Number(value) || 0));
}

function thresholdMarkings(thresholds, metric) {
  if (!thresholds) return {};
  const t = thresholds[metric];
  if (!t) return {};
  const lines = [];
  const areas = [];
  if (t.warning !== null && t.warning !== undefined) {
    lines.push({ yAxis: t.warning, label: { formatter: "Warn", position: "insideEndTop", fontSize: 10, color: COLOR_WARN }, lineStyle: { color: COLOR_WARN, type: "dashed", width: 1.5 } });
    if (t.critical !== null && t.critical !== undefined) {
      areas.push([{ yAxis: t.warning, itemStyle: { color: "rgba(227,163,43,0.06)" } }, { yAxis: t.critical }]);
    }
  }
  if (t.critical !== null && t.critical !== undefined) {
    lines.push({ yAxis: t.critical, label: { formatter: "Crit", position: "insideEndTop", fontSize: 10, color: COLOR_DANGER }, lineStyle: { color: COLOR_DANGER, type: "dashed", width: 1.5 } });
    areas.push([{ yAxis: t.critical, itemStyle: { color: "rgba(237,90,98,0.06)" } }, { yAxis: t.critical >= 0 ? t.critical + Math.abs(t.critical || 1) : t.critical - Math.abs(t.critical || 1) }]);
  }
  if (t.low !== null && t.low !== undefined) {
    lines.push({ yAxis: t.low, label: { formatter: "Low", position: "insideEndTop", fontSize: 10, color: COLOR_WARN }, lineStyle: { color: COLOR_WARN, type: "dashed", width: 1.5 } });
  }
  if (t.high !== null && t.high !== undefined) {
    lines.push({ yAxis: t.high, label: { formatter: "High", position: "insideEndTop", fontSize: 10, color: COLOR_WARN }, lineStyle: { color: COLOR_WARN, type: "dashed", width: 1.5 } });
  }
  return {
    markLine: lines.length ? { silent: true, symbol: "none", data: lines } : undefined,
    markArea: areas.length ? { silent: true, data: areas } : undefined,
  };
}

function CompactList({ rows, render, empty }) {
  if (!rows.length) return <Empty>{empty}</Empty>;
  return <div className="compact-list">{rows.map((row) => <div className="compact-item" key={row.id}>{render(row)}</div>)}</div>;
}

function metricLabel(metric) {
  return {
    vibration: "Vibration",
    temperature_c: "Temperature",
    current_a: "Current",
    pressure_kpa: "Estimated Pressure",
    hp_1st: "HP 1st",
    lp_1st: "LP 1st",
    hp_2nd: "HP 2nd",
    lp_2nd: "LP 2nd",
    temperature_hi: "Temperature High",
    temperature_lo: "Temperature Low",
  }[metric] || metric;
}

function busyLabel(value) {
  if (value === null || value === undefined) return "OFF";
  const numeric = Number(value);
  if (!Number.isNaN(numeric)) return numeric === 1 ? "ON" : "OFF";
  return ["1", "on", "true", "busy"].includes(String(value).trim().toLowerCase()) ? "ON" : "OFF";
}

function sensorNumber(value) {
  return value === null || value === undefined || value === "" ? null : (Number.isFinite(Number(value)) ? Number(value) : null);
}

function baseAxis(labels) {
  const zoomStart = (labels?.length || 0) > 150 ? 50 : 0;
  return {
    backgroundColor: "transparent",
    animation: false,
    tooltip: { trigger: "axis", confine: true, transitionDuration: 0.15, axisPointer: { type: "cross", label: { backgroundColor: "#273744" } } },
    legend: { top: 2, textStyle: { color: CHART_AXIS } },
    grid: { left: 54, right: 48, top: 48, bottom: 66 },
    dataZoom: [
      { type: "inside", start: zoomStart, end: 100, zoomOnMouseWheel: true, moveOnMouseMove: true },
      { type: "slider", start: zoomStart, end: 100, height: 18, bottom: 12, borderColor: CHART_GRID, fillerColor: "rgba(79, 150, 209, 0.16)", handleStyle: { color: COLOR_BLUE } },
    ],
    xAxis: { type: "category", data: labels, boundaryGap: false, axisLabel: { color: CHART_AXIS, hideOverlap: true }, axisLine: { lineStyle: { color: CHART_GRID } } },
  };
}

function overviewTrend(rows, thresholds) {
  const labels = rows.map(r => new Date(r.recorded_at).toLocaleTimeString());
  const pAxis = pressureAxis(rows.map(r => r.pressure_kpa));
  return {
    ...baseAxis(labels), color:[COLOR_BLUE,COLOR_WARN,COLOR_TEAL],
    grid:{left:65,right:125,top:55,bottom:66},
    yAxis:[
      {type:"value",name:"Current (A)",min:0,scale:true,axisLabel:{color:CHART_AXIS},splitLine:{lineStyle:{color:CHART_GRID}}},
      {type:"value",name:"Vibration (G rms)",position:"right",scale:true,axisLabel:{color:CHART_AXIS},splitLine:{show:false}},
      {...pAxis,name:"Est. pressure (kPa)",nameLocation:"middle",nameGap:38,nameRotate:90,nameTextStyle:{color:CHART_AXIS},position:"right",offset:65,axisLabel:{color:CHART_AXIS},splitLine:{show:false}},
    ],
    series:[line("Current A",rows.map(r=>r.current_a)),line("Vibration G rms",rows.map(r=>r.vibration),1),line("Estimated pressure kPa",rows.map(r=>r.pressure_kpa),2)]
  };
}

function thermalTrend(rows) {
  return {
    ...baseAxis(rows.map(r=>new Date(r.recorded_at).toLocaleTimeString())),color:[COLOR_TEAL],
    yAxis:{...pressureAxis(rows.map(r=>r.pressure_kpa)),name:"kPa",nameTextStyle:{color:CHART_AXIS},axisLabel:{color:CHART_AXIS},splitLine:{lineStyle:{color:CHART_GRID}}},
    series:[line("Estimated pressure kPa",rows.map(r=>r.pressure_kpa))]
  };
}

function singleTrend(rows, key, name, color, thresholds, metricKey) {
  const labels = rows.map((r) => new Date(r.recorded_at).toLocaleTimeString());
  const marks = thresholdMarkings(thresholds, metricKey || key);
  return {
    ...baseAxis(labels),
    color: [color],
    yAxis: { type: "value", axisLabel: { color: CHART_AXIS }, splitLine: { lineStyle: { color: CHART_GRID } } },
    series: [{ ...line(name, rows.map((r) => r[key])), ...marks }],
  };
}

function vibrationTrend(rows, thresholds) {
  const labels = rows.map((r) => new Date(r.recorded_at).toLocaleTimeString());
  const vibMarks = thresholdMarkings(thresholds, "vibration");
  return {
    ...baseAxis(labels),
    color: [COLOR_BLUE, COLOR_DANGER, COLOR_TEAL, COLOR_WARN],
    yAxis: { type: "value", axisLabel: { color: CHART_AXIS }, splitLine: { lineStyle: { color: CHART_GRID } } },
    series: [
      { ...line("Vibration G rms", rows.map((r) => r.vibration)), ...vibMarks },
      line("Ax", rows.map((r) => r.accel_x)),
      line("Ay", rows.map((r) => r.accel_y)),
      line("Az", rows.map((r) => r.accel_z)),
    ],
  };
}

function line(name, data, yAxisIndex = 0) {
  return {
    name,
    data,
    yAxisIndex,
    type: "line",
    smooth: 0.25,
    showSymbol: data.length < 25,
    symbol: "circle",
    symbolSize: 5,
    connectNulls: false,
    lineStyle: { width: 2.2 },
    emphasis: { focus: "series", lineStyle: { width: 3.4 } },
  };
}

function worstModule(device) {
  const rank = { OFFLINE: 0, NORMAL: 1, MONITORING: 1, UNDER_MAINTENANCE: 2, WATCH: 3, WARNING: 3, MAINTENANCE_REQUIRED: 4 };
  return [...activeModules(device)].sort((a, b) => (rank[b.status] || 0) - (rank[a.status] || 0))[0];
}

function severityRank(status) {
  return {
    OFFLINE: 7,
    MAINTENANCE_REQUIRED: 6,
    WARNING: 5,
    WATCH: 4,
    UNDER_MAINTENANCE: 3,
    MONITORING: 1,
    NORMAL: 1,
    GOOD: 1,
  }[status] || 0;
}

function statusColor(status) {
  if (status === "NOT_EVALUATED" || status === "OFFLINE") return COLOR_OFFLINE;
  if (status === "MAINTENANCE_REQUIRED") return COLOR_DANGER;
  if (status === "UNDER_MAINTENANCE") return COLOR_BLUE;
  if (status === "MONITORING") return COLOR_GOOD;
  if (status === "WARNING" || status === "WATCH") return COLOR_WARN;
  return COLOR_TEAL;
}

function buildOverviewAlerts(alerts, devices, workOrders) {
  const realAlerts = alerts.filter((alert) => !alert.acknowledged).map((alert) => ({
    id: `alert-${alert.id}`,
    title: alert.title,
    device: alert.machine_code || alert.display_name || `Device ${alert.device_id}`,
    age: ago(Math.max(0, Math.floor((Date.now() - new Date(alert.recorded_at).getTime()) / 1000))),
    severity: alert.severity || "info",
  }));
  const deviceAlerts = devices
    .filter((device) => !isUnregisteredDevice(device) && (["MAINTENANCE_REQUIRED", "WARNING", "WATCH"].includes(device.status) || device.connection_state !== "ONLINE"))
    .map((device) => ({
      id: `device-${device.id}`,
      title: device.connection_state !== "ONLINE" ? "Heartbeat lost - attempting reconnect" : `${device.display_name || device.machine_code} requires attention`,
      device: device.device_uid || device.machine_code,
      age: ago(device.seconds_since_seen),
      severity: device.status === "MAINTENANCE_REQUIRED" ? "critical" : device.connection_state !== "ONLINE" ? "info" : "warning",
    }));
  const workAlerts = workOrders
    .filter((order) => order.status !== "DONE" && order.status !== "CANCELLED")
    .map((order) => ({
      id: `work-${order.id}`,
      title: order.title,
      device: order.machine_code || order.display_name || "Work order",
      age: order.status,
      severity: order.priority === "CRITICAL" ? "critical" : order.priority === "HIGH" ? "warning" : "info",
    }));
  const weight = { critical: 0, warning: 1, info: 2 };
  const seen = new Set();
  return [...realAlerts, ...deviceAlerts, ...workAlerts]
    .sort((a, b) => (weight[a.severity] ?? 3) - (weight[b.severity] ?? 3))
    .filter((item) => {
      const key = `${item.severity}:${item.title}:${item.device}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    })
    .slice(0, 6);
}

const sparklineCache = new WeakMap();
function metricSparklineOption(rows, key, color, unit = "", label = "") {
  let options = sparklineCache.get(rows);
  if (!options) { options = new Map(); sparklineCache.set(rows, options); }
  const signature = JSON.stringify([key, color, unit, label]);
  if (!options.has(signature)) options.set(signature, buildMetricSparklineOption(rows, key, color, unit, label));
  return options.get(signature);
}

function buildMetricSparklineOption(rows, key, color, unit = "", label = "") {
  const data = (rows || [])
    .map((row) => [row.recorded_at || row.timestamp, sensorNumber(row[key])])
    .filter(([time, value]) => time && Number.isFinite(value));
  const values = data.map(([, value]) => value);
  const hasRange = values.length > 1;
  const rawMin = hasRange ? Math.min(...values) : (values[0] ?? 0);
  const rawMax = hasRange ? Math.max(...values) : (values[0] ?? 0);
  const rawDiff = rawMax - rawMin;

  // Protect against micro-fluctuation scaling (e.g. 0.1 deg C oscillation becoming giant square wave)
  const minSpan = String(key).includes("temperature") || String(key).includes("temp") ? 3.0
                : (String(key).includes("hp") || String(key).includes("lp") || String(key).includes("pressure")) ? 4.0
                : (String(key).includes("valve") || String(key).includes("busy")) ? 10.0
                : 1.5;
  const effectiveSpan = Math.max(rawDiff, minSpan);
  const mid = (rawMin + rawMax) / 2;
  const padding = effectiveSpan * 0.18;
  const yMin = hasRange ? (rawDiff < minSpan ? mid - (effectiveSpan / 2) - padding : rawMin - padding) : undefined;
  const yMax = hasRange ? (rawDiff < minSpan ? mid + (effectiveSpan / 2) + padding : rawMax + padding) : undefined;

  return {
    backgroundColor: "transparent",
    animation: false,
    tooltip: {
      trigger: "axis",
      confine: true,
      transitionDuration: 0.1,
      backgroundColor: "#0b121a",
      borderColor: "#26384a",
      borderWidth: 1,
      padding: [6, 10],
      textStyle: { color: "#e5eef8", fontSize: 12 },
      axisPointer: {
        type: "cross",
        lineStyle: { color: CHART_AXIS, type: "dashed", width: 1.2 },
        label: { backgroundColor: "#1e293b", precision: 1 },
      },
      formatter: (params) => {
        if (!params || !params.length) return "";
        const p = params[0];
        const rawTime = p.value ? p.value[0] : p.name;
        const timeStr = rawTime ? new Date(rawTime).toLocaleTimeString() : "";
        const val = Number.isFinite(p.value?.[1]) ? n(p.value[1], 1) : Number.isFinite(p.value) ? n(p.value, 1) : "--";
        const title = label || metricLabel(key) || p.seriesName;
        return `<div style="font-size:11px;font-weight:600;margin-bottom:3px;opacity:0.75">${timeStr}</div>
                <div style="display:flex;align-items:center;gap:6px;font-size:13px;font-weight:600">
                  <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:${color};flex-shrink:0"></span>
                  <span style="opacity:0.85">${title}:</span>
                  <strong style="font-size:14px;font-weight:700;margin-left:2px">${val}${unit ? ` ${unit}` : ""}</strong>
                </div>`;
      },
    },
    grid: { left: 0, right: 0, top: 12, bottom: 0 },
    xAxis: { type: "time", show: false },
    yAxis: {
      type: "value",
      show: false,
      scale: true,
      min: yMin,
      max: yMax,
    },
    series: [{
      name: label || metricLabel(key),
      type: "line",
      smooth: 0.35,
      symbol: data.length <= 1 ? "circle" : "none",
      symbolSize: 6,
      data,
      lineStyle: { color, width: 2.8 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: `${color}66` },
          { offset: 1, color: `${color}04` },
        ]),
      },
    }],
  };
}

function sparklineOption(_seed, color) {
  return {
    backgroundColor: "transparent",
    grid: { left: 0, right: 0, top: 12, bottom: 0 },
    xAxis: { type: "category", show: false, data: [] },
    yAxis: { type: "value", show: false, scale: true },
    series: [{
      type: "line",
      smooth: true,
      symbol: "none",
      data: [],
      lineStyle: { color, width: 3 },
      areaStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [{ offset: 0, color: `${color}66` }, { offset: 1, color: `${color}05` }]) },
    }],
  };
}

createRoot(document.getElementById("root")).render(<App />);
