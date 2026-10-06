import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import patch

from app.telemetry_sources import MySQLTelemetryPoller, ReadOnlyTelemetrySources


class FakeSources:
    def __init__(self, count):
        self.samples = [SimpleNamespace(source_id=f"sample-{i}", machine_code="MX001", module_code="vacuum-pump") for i in range(count)]
        self.calls = 0

    def latest_samples(self):
        self.calls += 1
        return self.samples if self.calls == 1 else []

    def health_for(self, *_):
        return None


class PollerBatchTests(unittest.TestCase):
    def test_many_samples_publish_one_cycle(self):
        source = FakeSources(160)
        poller = MySQLTelemetryPoller(source)
        published = threading.Event()
        processed = []
        cycles = []

        def on_cycle():
            cycles.append(len(processed))
            published.set()

        poller.start(lambda sample: processed.append(sample.source_id), on_cycle=on_cycle)
        self.assertTrue(published.wait(timeout=2))
        poller.stop()
        self.assertEqual(len(processed), 160)
        self.assertEqual(cycles, [160])

    def test_same_history_requested_by_many_tabs_queries_source_once(self):
        sources = ReadOnlyTelemetrySources()
        sample = object()
        with patch.object(sources, "source_configured", return_value=True), \
             patch.object(sources, "_compressor_history", return_value=[sample]) as query:
            with ThreadPoolExecutor(max_workers=12) as pool:
                rows = list(pool.map(lambda _: sources.history_for(
                    "compressor:MX001", "compressor-m1", 2000,
                    source="compressor", source_device_key="MX001"), range(12)))
        self.assertEqual(query.call_count, 1)
        self.assertTrue(all(result == [sample] for result in rows))

    def test_history_and_metric_panels_share_compressor_source_read(self):
        sources = ReadOnlyTelemetrySources()
        samples = [object() for _ in range(3000)]
        with patch.object(sources, "source_configured", return_value=True), \
             patch.object(sources, "_compressor_history", return_value=samples) as query:
            history = sources.history_for("compressor:MX001", "compressor-m1", 2000,
                                          source="compressor", source_device_key="MX001")
            metrics = sources.history_for("compressor:MX001", "compressor-m1", 3000,
                                          source="compressor", source_device_key="MX001")
        self.assertEqual(query.call_count, 1)
        self.assertEqual(len(history), 2000)
        self.assertEqual(len(metrics), 3000)


if __name__ == "__main__":
    unittest.main()
