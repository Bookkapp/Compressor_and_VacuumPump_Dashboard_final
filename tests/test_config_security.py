import unittest
from unittest.mock import patch

from app.config import resolve_secret_key, validate_production_passwords
from app.db import seed_users


class SecretKeyTests(unittest.TestCase):
    def test_development_uses_unpredictable_key_when_unset(self):
        first = resolve_secret_key("", "development")
        second = resolve_secret_key("", "development")
        self.assertGreaterEqual(len(first), 32)
        self.assertNotEqual(first, second)

    def test_production_rejects_missing_or_weak_key(self):
        for key in (None, "", "short", "change-this-secret-before-production"):
            with self.subTest(key=key), self.assertRaises(ValueError):
                resolve_secret_key(key, "production")

    def test_explicit_strong_key_is_stable(self):
        key = "a-unique-secret-key-with-at-least-32-chars"
        self.assertEqual(resolve_secret_key(key, "production"), key)

    def test_production_rejects_default_or_short_bootstrap_passwords(self):
        for admin, user in (("ADIIOT", "ADIMNT"), ("short", "a-long-enough-user-password"), ("same-password-1234", "same-password-1234")):
            with self.subTest(admin=admin), self.assertRaises(ValueError):
                validate_production_passwords("production", admin, user)
        validate_production_passwords("production", "a-strong-admin-password", "a-separate-user-password")

    def test_seed_users_does_not_overwrite_existing_accounts(self):
        with patch("app.db.execute_many") as execute_many:
            seed_users()
        sql = execute_many.call_args.args[0]
        self.assertIn("ON DUPLICATE KEY UPDATE id = id", sql)
        self.assertNotIn("is_active = 1", sql)
        self.assertNotIn("password_hash = VALUES", sql)


if __name__ == "__main__":
    unittest.main()
