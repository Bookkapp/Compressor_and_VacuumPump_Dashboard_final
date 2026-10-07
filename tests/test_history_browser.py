from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import time
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from app import history_browser as browser


class HistoryBrowserTests(unittest.TestCase):
    def setUp(self):
        browser._cache.clear()
        browser._stats.clear()

    def test_timezone_and_half_open_window_validation(self):
        start, end = browser.history_window("2026-09-16T00:00:00Z", "2026-09-17T00:00:00Z")
        self.assertEqual(start, datetime(2026, 9, 16, 7))
        self.assertEqual(end, datetime(2026, 9, 17, 7))
        self.assertEqual(browser.history_window(None, None), (None, None))
        for first, last in [("bad", "bad"), (None, "2026-09-17"), ("2026-09-17", "2026-09-16"), ("2026-09-01", "2026-10-03")]:
            with self.assertRaises(HTTPException) as error:
                browser.history_window(first, last)
            self.assertEqual(error.exception.status_code, 422)

    def test_raw_sql_filters_source_and_dates_before_page_limit(self):
        first, last = datetime(2026, 9, 16), datetime(2026, 9, 17)
        with patch.object(browser.telemetry_sources, "_query", side_effect=[
            [{"total": 500, "first_at": first, "last_at": last}], [{"id": 55}],
        ]) as query:
            result = browser.source_window("vacuum", "VP017", first, last, 100, 200, False)
        sql, params = query.call_args.args[1:]
        self.assertLess(sql.index("WHERE"), sql.index("LIMIT"))
        self.assertIn("`recorded_at` >= %s AND `recorded_at` < %s", sql)
        self.assertEqual(params, ("VP017", first, last, 100, 200))
        self.assertEqual(result["total"], 500)
        self.assertFalse(result["sampled"])
        self.assertTrue(query.call_args.kwargs["history"])

    def test_sampling_uses_source_time_and_pk_ties_and_bounded_buckets(self):
        first, last = datetime(2026, 9, 1), datetime(2026, 9, 30)
        with patch.object(browser.telemetry_sources, "_query", side_effect=[
            [{"total": 40000, "first_at": first, "last_at": last}], [{"id": 2}, {"id": 1}],
        ]) as query:
            result = browser.source_window("compressor", "777", first, last, 1200, 0, True)
        sql, params = query.call_args.args[1:]
        self.assertIn("DATE_FORMAT", sql)
        self.assertIn("LPAD(id, 20", sql)
        self.assertIn("TIMESTAMPDIFF(MICROSECOND", sql)
        self.assertEqual(params[:3], ("777", first, last))
        self.assertLessEqual(((last - first).total_seconds() * 1e6) // params[-1] + 1, 600)
        self.assertTrue(result["sampled"])
        self.assertEqual(result["sampling"], "time_bucket_first_last")

    def test_latest_chart_is_a_bounded_read_without_full_source_count(self):
        with patch.object(browser.telemetry_sources, "_query", return_value=[
            {"id": 2, "recorded_at": datetime(2026, 9, 16, 1)},
            {"id": 1, "recorded_at": datetime(2026, 9, 16)},
        ]) as query:
            result = browser.source_window("vacuum", "VP017", None, None, 1200, 0, True)
        self.assertEqual(query.call_count, 1)
        self.assertNotIn("COUNT", query.call_args.args[1])
        self.assertEqual(query.call_args.args[2], ("VP017", 1200))
        self.assertEqual([row["id"] for row in result["raw_rows"]], [1, 2])
        self.assertTrue(result["latest_limited"])

    def test_cache_separates_source_machine_time_page_and_chart_mode(self):
        def query(source, sql, params, **kwargs):
            if "COUNT(*)" in sql:
                return [{"total": 10, "first_at": datetime(2026, 9, 1), "last_at": datetime(2026, 9, 2)}]
            return [{"id": params[0], "source": source}]
        with patch.object(browser.telemetry_sources, "_query", side_effect=query) as call:
            args = ("compressor", "777", datetime(2026, 9, 1), datetime(2026, 9, 2), 100, 0, False)
            a = browser.source_window(*args)
            self.assertEqual(browser.source_window(*args), a)
            self.assertEqual(call.call_count, 2)
            for changed in [(*args[:5], 100, False), (*args[:6], True), ("compressor", "080", *args[2:]), ("vacuum", "777", *args[2:]), (*args[:3], datetime(2026, 9, 3), *args[4:])]:
                browser.source_window(*changed)
            self.assertEqual(call.call_count, 10)

    def test_concurrent_identical_requests_share_source_reads(self):
        def query(source, sql, params, **kwargs):
            time.sleep(.005)
            return [{"total": 1, "first_at": datetime(2026, 9, 1), "last_at": datetime(2026, 9, 1)}] if "COUNT(*)" in sql else [{"id": 1}]
        with patch.object(browser.telemetry_sources, "_query", side_effect=query) as call:
            with ThreadPoolExecutor(max_workers=8) as executor:
                result = list(executor.map(lambda _: browser.source_window("vacuum", "17", None, None, 100, 0, False), range(8)))
            self.assertEqual(call.call_count, 2)
            self.assertTrue(all(item == result[0] for item in result))

    def module(self, source="compressor"):
        return {"machine_code": "HT9046MX-777", "module_id": 5, "module_code": "compressor-m5" if source == "compressor" else "vacuum-pump", "module_name": "M5", "telemetry_source": source, "source_device_key": "777"}

    def test_module_ownership_and_source_signals_rejected_before_source_read(self):
        with patch.object(browser, "fetch_one", return_value=None), patch.object(browser, "source_window") as query:
            with self.assertRaises(HTTPException) as error:
                browser.browse_history(400, 99)
            self.assertEqual(error.exception.status_code, 404)
            query.assert_not_called()
        with patch.object(browser, "fetch_one", return_value=self.module()), patch.object(browser, "source_window") as query:
            with self.assertRaises(HTTPException) as error:
                browser.browse_history(400, 5, chart=True, signals="accel_x")
            self.assertEqual(error.exception.status_code, 422)
            query.assert_not_called()

    def test_compressor_nulls_status_and_requested_module_not_other_module(self):
        raw = [{"id": 8, "machine_number": "777", "recorded_at": datetime(2026, 9, 16), "Hp_1st_1": 999, "Status_5": "Off", "SV_5": "On"},
               {"id": 9, "machine_number": "777", "recorded_at": datetime(2026, 9, 16, 0, 1), "Hp_1st_5": 12.5}]
        with patch.object(browser, "fetch_one", return_value=self.module()), patch.object(browser.telemetry_sources, "source_configured", return_value=True), patch.object(browser, "source_window", return_value={"raw_rows": raw, "total": 2, "sampled": False}):
            result = browser.browse_history(400, 5)
        self.assertIsNone(result["rows"][0]["hp_1st"])
        self.assertEqual(result["rows"][0]["operating_status"], "Off")
        self.assertEqual(result["rows"][0]["set_valve_status"], "On")
        self.assertNotIn("accel_x", result["rows"][0])
        self.assertEqual(result["rows"][0]["recorded_at"], "2026-09-16T00:00:00+07:00")
        self.assertIsNotNone(result["rows"][1]["hp_1st"])

    def test_vacuum_only_real_family_columns_and_estimated_pressure(self):
        for identity_column in ("devices_id", "device_id"):
            with self.subTest(identity_column=identity_column):
                raw = [{"id": 9, identity_column: "777", "recorded_at": datetime(2026, 9, 16), "temperature": 45, "vibration": 1.02, "current_amp": None}]
                with patch.object(browser.settings, "vacuum_device_column", identity_column), patch.object(browser, "fetch_one", return_value=self.module("vacuum")), patch.object(browser.telemetry_sources, "source_configured", return_value=True), patch.object(browser, "source_window", return_value={"raw_rows": raw, "total": 1, "sampled": False}):
                    result = browser.browse_history(400, 5, chart=True)
                self.assertEqual(result["rows"][0]["temperature_c"], 45)
                self.assertAlmostEqual(result["rows"][0]["pressure_kpa"], -73.572, places=3)
                self.assertIsNone(result["rows"][0]["current_a"])
                self.assertNotIn("hp_1st", result["rows"][0])


if __name__ == "__main__":
    unittest.main()
