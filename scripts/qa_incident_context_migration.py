"""Local, additive metadata migration; no source/WO/log content mutation."""
from app.config import settings
from app.db import connection, migrate_incident_evidence


def main():
    if settings.db_host not in {"localhost", "127.0.0.1", "::1"}:
        raise RuntimeError("This QA runner is for localhost metadata only")
    with connection() as conn, conn.cursor() as cur:
        migrate_incident_evidence(cur)
        migrate_incident_evidence(cur)  # idempotency
        cur.execute("SHOW COLUMNS FROM pm_work_orders")
        fields = {row["Field"] for row in cur.fetchall()}
        assert {"report_origin", "event_started_at", "event_ended_at", "event_timezone", "event_time_precision"} <= fields
        cur.execute("SHOW COLUMNS FROM pm_maintenance_logs LIKE 'incident_context_json'")
        assert cur.fetchone()
    print("Local metadata incident-context migration passed twice; no work/source rows changed")


if __name__ == "__main__":
    main()
