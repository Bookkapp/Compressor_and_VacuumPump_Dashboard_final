// Handler charts and relationships share the same bounded, source-specific rows.
export const COMPRESSOR_SIGNALS = Object.freeze(["hp_1st", "lp_1st", "hp_2nd", "lp_2nd", "temperature_hi", "temperature_lo", "valve"]);
export const VACUUM_SIGNALS = Object.freeze(["temperature_c", "pressure_kpa", "current_a", "vibration", "accel_x", "accel_y", "accel_z"]);

export function historyRowsEqual(previous, next) {
  if (previous === next) return true;
  if (!previous || previous.length !== next.length) return false;
  return previous.every((row, index) => {
    const other = next[index];
    const keys = Object.keys(row);
    return keys.length === Object.keys(other).length && keys.every(key => Object.is(row[key], other[key]));
  });
}

function number(value) {
  if (value === null || value === undefined || value === "" || typeof value === "boolean") return null;
  const result = Number(value);
  return Number.isFinite(result) ? result : null;
}

function pairs(rows, x, y) {
  return rows.flatMap(row => {
    const a = number(row[x]), b = number(row[y]);
    return row.recorded_at && a !== null && b !== null ? [{ recorded_at: row.recorded_at, x: a, y: b }] : [];
  });
}

// Same paired-sample Pearson formula as app.analytics; never fill missing values.
export function pearson(points) {
  if (points.length < 3) return null;
  const mx = points.reduce((sum, p) => sum + p.x, 0) / points.length;
  const my = points.reduce((sum, p) => sum + p.y, 0) / points.length;
  let numerator = 0, dx = 0, dy = 0;
  for (const point of points) {
    const x = point.x - mx, y = point.y - my;
    numerator += x * y; dx += x * x; dy += y * y;
  }
  const denominator = Math.sqrt(dx * dy);
  return denominator ? Math.round(numerator / denominator * 10000) / 10000 : null;
}

function windowFor(rows) {
  return { from: rows[0]?.recorded_at ?? null, to: rows.at(-1)?.recorded_at ?? null };
}

export function historyCorrelation(rows, signals = COMPRESSOR_SIGNALS) {
  const matrix = signals.map(() => signals.map(() => null));
  for (let x = 0; x < signals.length; x++) {
    for (let y = x; y < signals.length; y++) {
      const value = pearson(pairs(rows, signals[x], signals[y]));
      matrix[x][y] = value; matrix[y][x] = value;
    }
  }
  return {
    signals, matrix, samples: rows.filter(row => row.recorded_at && signals.some(key => number(row[key]) !== null)).length,
    analysis_window: windowFor(rows), method: "pearson",
  };
}

export function historyRelationship(rows, x_signal, y_signal) {
  const paired = pairs(rows, x_signal, y_signal);
  const step = Math.max(1, Math.ceil(paired.length / 1200));
  const points = step === 1 ? paired : paired.filter((_, index) => index % step === 0);
  return { x_signal, y_signal, points, correlation: pearson(points), samples: points.length, analysis_window: windowFor(rows), method: "pearson" };
}
