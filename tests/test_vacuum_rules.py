from datetime import datetime
import unittest

from app.diagnostics import (
    compute_diagnostics,
    estimate_vacuum_pressure_kpa,
    vacuum_pressure_condition,
)


class VacuumRuleTests(unittest.TestCase):
    def test_pressure_is_inverse_of_supplied_vibration_calibration(self) -> None:
        # V = -0.0439P - 2.2098, using P=-80 kPa.
        self.assertAlmostEqual(estimate_vacuum_pressure_kpa(1.3022), -80.0, places=3)
        self.assertIsNone(estimate_vacuum_pressure_kpa(None))

    def test_pressure_boundaries_match_confirmed_rule(self) -> None:
        self.assertEqual(vacuum_pressure_condition(-90), ("NORMAL", None))
        self.assertEqual(vacuum_pressure_condition(-70), ("NORMAL", None))
        self.assertEqual(vacuum_pressure_condition(-69.9)[0], "WARNING")
        self.assertEqual(vacuum_pressure_condition(-60)[0], "WARNING")
        self.assertEqual(vacuum_pressure_condition(-59.9)[0], "MAINTENANCE_REQUIRED")
        self.assertEqual(vacuum_pressure_condition(-90.1)[0], "WARNING")

    def test_diagnostics_generate_one_pressure_issue_key_for_escalation(self) -> None:
        warning = compute_diagnostics(
            [{"recorded_at": datetime(2026, 9, 16, 8), "vibration": 0.6437}],
            source="vacuum",
        )
        critical = compute_diagnostics(
            [{"recorded_at": datetime(2026, 9, 16, 9), "vibration": 0.2047}],
            source="vacuum",
        )
        self.assertEqual(warning["alerts"][0]["severity"], "warning")
        self.assertEqual(critical["alerts"][0]["severity"], "critical")
        self.assertEqual(warning["alerts"][0]["issue_key"], "vacuum_pressure_high")
        self.assertEqual(critical["alerts"][0]["issue_key"], "vacuum_pressure_high")
        self.assertIn("no pressure sensor", warning["ai_notes"].lower())


if __name__ == "__main__":
    unittest.main()
