from datetime import datetime
import unittest

from unittest.mock import patch

from app.config import settings
from app.telemetry_sources import ReadOnlyTelemetrySources
from app.services import compressor_condition_state


class TelemetrySourceMappingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.sources = ReadOnlyTelemetrySources()

    def test_explicit_ml_condition_is_not_overridden_by_local_score_band(self) -> None:
        self.assertEqual(compressor_condition_state("NORMAL", 76), "NORMAL")
        self.assertEqual(compressor_condition_state("WATCH", 95), "WATCH")

    def test_vacuum_row_uses_devices_id_as_the_external_device_key(self) -> None:
        sample = self.sources._vacuum_sample(
            {
                "id": 42,
                "devices_id": "30",
                "recorded_at": "2026-09-03 10:00:00",
                "temperature": 42.5,
                "accel_x": 0.1,
                "accel_y": 0.2,
                "accel_z": 0.9,
                "vibration": 1.02,
                "current_amp": 3.8,
            }
        )
        self.assertIsNotNone(sample)
        assert sample is not None
        self.assertEqual(sample.device_uid, "vacuum:30")
        self.assertEqual(sample.machine_code, "HT9046MX-030")
        self.assertEqual(sample.display_name, "HT9046MX-030")
        self.assertEqual(sample.module_code, "vacuum-pump")
        self.assertEqual(sample.current_a, 3.8)
        self.assertAlmostEqual(sample.pressure_kpa, -73.572, places=3)
        self.assertEqual(sample.metrics["vibration"], (1.02, "G rms"))
        self.assertEqual(sample.metrics["estimated_pressure_kpa"], (-73.572, "kPa"))
        self.assertEqual(sample.recorded_at, datetime(2026, 9, 3, 10, 0, 0))

    def test_wide_compressor_row_becomes_one_sample_per_detected_module(self) -> None:
        with patch.object(settings, "compressor_sensor_scale", "0.1"):
            samples = self.sources._compressor_samples(
                {
                    "machine_number": "57",
                    "recorded_at": "2026-09-03 10:00:00",
                    "Hp_1st_1": 1200,
                    "Lp_1st_1": 300,
                    "Hp_2nd_1": 2100,
                    "Lp_2nd_1": 520,
                    "Valve_1": 60,
                    "TempHi_1": 700,
                    "TempLo_1": 200,
                    "Status_1": "On",
                    "Busy_1": 0,
                    "SV_1": "On",
                }
            )
        self.assertEqual(len(samples), 1)
        sample = samples[0]
        self.assertEqual(sample.device_uid, "compressor:57")
        self.assertEqual(sample.machine_code, "HT9046MX-057")
        self.assertEqual(sample.display_name, "HT9046MX-057")
        self.assertEqual(sample.operating_status, "On")
        self.assertEqual(sample.module_code, "compressor-m1")
        self.assertEqual(sample.temperature_c, 70.0)
        self.assertEqual(sample.pressure_kpa, 120.0)
        self.assertEqual(sample.metrics["valve"][0], 60.0)

    def test_compressor_large_value_does_not_change_explicit_unit_scale(self) -> None:
        with patch.object(settings, "compressor_sensor_scale", "1"):
            samples = self.sources._compressor_samples({
                "machine_number": "70",
                "recorded_at": "2026-09-03 13:35:04",
                "Hp_1st_5": 151.9,
                "Lp_1st_5": 30.4,
                "Hp_2nd_5": 314.8,
                "Lp_2nd_5": 38.3,
                "TempHi_5": 95.0,
                "TempLo_5": -29.1,
            })
        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0].pressure_kpa, 151.9)
        self.assertEqual(samples[0].temperature_c, 95.0)
        self.assertEqual(samples[0].metrics["hp_2nd"], (314.8, None))

    def test_compressor_health_score_contract_maps_machine_and_module(self) -> None:
        rows = [{
            "machine_number": "57",
            "module_id": "M2",
            "recorded_at": "2026-09-03 10:00:00",
            "health_score": 81.4,
            "health_condition": "WATCH",
            "model_version": "compressor-2026.09",
        }]
        with patch.object(settings, "compressor_health_enabled", True), patch.object(
            self.sources, "_compressor_health_latest_rows", return_value=rows
        ):
            self.sources._refresh_compressor_health_scores()

        health = self.sources.health_for("HT9046MX-057", "compressor-m2")
        self.assertIsNotNone(health)
        assert health is not None
        self.assertEqual(health.module_number, 2)
        self.assertEqual(health.health_score, 81.4)
        self.assertEqual(health.condition, "WATCH")
        self.assertEqual(health.model_version, "compressor-2026.09")

    def test_history_row_preserves_source_columns_and_missing_axes(self):
        sample = self.sources._compressor_samples({
            "machine_number": "57", "recorded_at": "2026-09-30 10:00:00",
            "Hp_1st_1": 120, "TempHi_1": 70, "Busy_1": 1, "Status_1": "On", "SV_1": "Off",
        })[0]
        row = sample.history_row(1, 12)
        self.assertEqual(row["hp_1st"], sample.metrics["hp_1st"][0])
        self.assertEqual(row["busy"], 1)
        self.assertEqual(row["sv"], 0)
        self.assertEqual(row["operating_status"], "On")
        self.assertEqual(row["set_valve_status"], "Off")
        self.assertIsNone(row["accel_x"])
        self.assertNotIn("current_amp", row)
        vacuum = self.sources._vacuum_sample({"id": 1, "devices_id": 57, "recorded_at": "2026-09-30 10:00:00", "temperature": 42, "current_amp": 3, "accel_x": 0.1})
        self.assertEqual(vacuum.history_row(1, 11)["accel_x"], 0.1)
        self.assertNotIn("hp_1st", vacuum.history_row(1, 11))

    def test_concurrent_module_history_reuses_wide_read_without_crossing_machines(self):
        from concurrent.futures import ThreadPoolExecutor
        rows = [{"machine_number": "57", "recorded_at": "2026-09-30 10:00:00", "Hp_1st_1": 120, "Hp_1st_2": 220}]
        with patch.object(self.sources, "_query", return_value=rows) as query:
            with ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(lambda module: self.sources._compressor_history("57", module, 2000), [1, 2, 1, 2]))
            self.assertEqual(query.call_count, 1)
            self.assertEqual([result[0].module_code for result in results], ["compressor-m1", "compressor-m2", "compressor-m1", "compressor-m2"])
            self.sources._compressor_history("58", 1, 2000)
            self.assertEqual(query.call_count, 2)

    def test_history_range_does_not_shift_to_old_samples_or_fallback(self):
        from app.services import get_history, get_metric_history
        sample = self.sources._vacuum_sample({"id": 1, "devices_id": 57, "recorded_at": "2026-09-01 10:00:00", "temperature": 42})
        module = {"id": 11, "module_code": "vacuum-pump", "module_name": "Vacuum Pump", "telemetry_source": "vacuum", "source_device_key": "57"}
        with patch("app.services.fetch_one", return_value={"id": 1, "device_uid": "vacuum:57", "machine_code": "HT9046MX-057"}), patch("app.services.fetch_all", return_value=[module]) as fetch, patch("app.services.telemetry_sources.history_for", return_value=[sample]):
            self.assertEqual(get_history(1, 11, since="2026-09-30T09:00:00"), [])
            self.assertEqual(get_metric_history(1, 11, since="2026-09-30T09:00:00"), [])
            self.assertEqual(fetch.call_count, 2)

    def test_browser_utc_range_is_converted_to_source_local_time(self):
        from app.services import _parse_since
        with patch.object(settings, "app_timezone", "Asia/Bangkok"):
            self.assertEqual(_parse_since("2026-09-30T02:00:00Z"), datetime(2026, 9, 30, 9))
            self.assertEqual(_parse_since("2026-09-30T09:00:00+07:00"), datetime(2026, 9, 30, 9))

    def test_blocked_compressor_read_does_not_block_vacuum_or_status(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event
        entered, release = Event(), Event()
        sample = self.sources._vacuum_sample({"id": 1, "devices_id": "57", "recorded_at": "2026-09-30 10:00:00"})
        def blocked(*args):
            entered.set()
            self.assertTrue(release.wait(3))
            return []
        with patch.object(self.sources, "source_configured", return_value=True), patch.object(self.sources, "_compressor_history", side_effect=blocked), patch.object(self.sources, "_vacuum_history", return_value=[sample]):
            with ThreadPoolExecutor(max_workers=3) as pool:
                compressor = pool.submit(self.sources.history_for, "compressor:57", "compressor-m1", 2000)
                self.assertTrue(entered.wait(1))
                try:
                    self.assertEqual(pool.submit(self.sources.history_for, "vacuum:57", "vacuum-pump", 2000).result(timeout=1), [sample])
                    pool.submit(self.sources.status).result(timeout=1)
                finally:
                    release.set()
                self.assertEqual(compressor.result(timeout=1), [])

    def test_compact_chart_response_keeps_nulls_and_legacy_database_rows(self):
        from app.main import devices_history
        from fastapi import HTTPException
        rows = [{"recorded_at": "2026-09-30T10:00:00", "hp_1st": 0, "lp_1st": None, "accel_x": None, "module_name": "M1"}]
        with patch("app.main.get_history", return_value=rows) as history:
            self.assertEqual(devices_history(1, 2, signals="hp_1st,lp_1st", token={}), [{"recorded_at": rows[0]["recorded_at"], "hp_1st": 0, "lp_1st": None}])
            self.assertEqual(devices_history(1, 2, token={}), rows)
            with self.assertRaises(HTTPException):
                devices_history(1, 2, signals="unknown_column", token={})
            self.assertEqual(history.call_count, 2)

    def test_history_pool_bounds_connections_and_never_shares_a_cursor(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Lock
        from time import sleep
        created, active = [], set()
        guard = Lock()
        test = self
        class Connection:
            def __init__(self):
                created.append(self)
            def ping(self, **kwargs): pass
            def close(self): pass
            def cursor(self):
                connection = self
                class Cursor:
                    def __enter__(self): return self
                    def __exit__(self, *args): pass
                    def execute(self, sql, params):
                        with guard:
                            test.assertNotIn(connection, active)
                            active.add(connection)
                        sleep(0.01)
                        self.value = params[0]
                    def fetchall(self):
                        with guard: active.remove(connection)
                        return [{"value": self.value}]
                return Cursor()
        with patch.object(self.sources, "_open_connection", side_effect=lambda source: Connection()):
            with ThreadPoolExecutor(max_workers=10) as pool:
                results = list(pool.map(lambda i: self.sources._query("compressor", "SELECT", (i,), history=True), range(10)))
        self.assertLessEqual(len(created), 4)
        self.assertEqual(results, [[{"value": i}] for i in range(10)])

    def test_batch_history_preserves_per_module_series(self):
        from app.main import devices_history_batch
        from fastapi import HTTPException
        with patch("app.main.devices_history", side_effect=lambda device, module, *args: [{"hp_1st": module}]) as history:
            self.assertEqual(devices_history_batch(1, "12,13,12", "hp_1st", token={}), {"12": [{"hp_1st": 12}], "13": [{"hp_1st": 13}]})
            self.assertEqual(history.call_count, 2)
            with self.assertRaises(HTTPException):
                devices_history_batch(1, ",", "hp_1st", token={})


if __name__ == "__main__":
    unittest.main()
