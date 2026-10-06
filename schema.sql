-- ADI HT9046 Predictive Maintenance schema.
-- Non-destructive: this script does not drop the database or old tables.
-- The FastAPI app also creates these pm_* tables automatically on startup.

CREATE DATABASE IF NOT EXISTS predictive_maintenance
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE predictive_maintenance;

CREATE TABLE IF NOT EXISTS pm_users (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    username VARCHAR(80) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(160) NULL,
    role ENUM('admin', 'user') NOT NULL DEFAULT 'user',
    is_active TINYINT(1) NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_pm_users_username (username),
    KEY idx_pm_users_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS pm_devices (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    device_uid VARCHAR(120) NOT NULL,
    machine_code VARCHAR(120) NOT NULL,
    display_name VARCHAR(160) NOT NULL,
    location VARCHAR(160) NULL,
    firmware_version VARCHAR(80) NULL,
    status ENUM('NORMAL', 'WATCH', 'WARNING', 'MAINTENANCE_REQUIRED', 'UNDER_MAINTENANCE', 'OFFLINE') NOT NULL DEFAULT 'OFFLINE',
    first_seen DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_pm_devices_uid (device_uid),
    KEY idx_pm_devices_machine (machine_code),
    KEY idx_pm_devices_status (status),
    KEY idx_pm_devices_last_seen (last_seen)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS pm_modules (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    device_id BIGINT UNSIGNED NOT NULL,
    module_code VARCHAR(100) NOT NULL,
    module_name VARCHAR(160) NOT NULL,
    module_type VARCHAR(120) NULL,
    status ENUM('NORMAL', 'WATCH', 'WARNING', 'MAINTENANCE_REQUIRED', 'UNDER_MAINTENANCE', 'OFFLINE') NOT NULL DEFAULT 'OFFLINE',
    thresholds_json JSON NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_pm_modules_device_code (device_id, module_code),
    KEY idx_pm_modules_status (status),
    CONSTRAINT fk_pm_modules_device
        FOREIGN KEY (device_id) REFERENCES pm_devices(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS pm_sensor_readings (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    device_id BIGINT UNSIGNED NOT NULL,
    module_id BIGINT UNSIGNED NOT NULL,
    recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source VARCHAR(40) NOT NULL DEFAULT 'mqtt',
    temperature_c DOUBLE NULL,
    pressure_kpa DOUBLE NULL,
    current_a DOUBLE NULL,
    accel_x DOUBLE NULL,
    accel_y DOUBLE NULL,
    accel_z DOUBLE NULL,
    vibration DOUBLE NULL,
    gyro_x DOUBLE NULL,
    gyro_y DOUBLE NULL,
    gyro_z DOUBLE NULL,
    raw_payload JSON NULL,
    PRIMARY KEY (id),
    KEY idx_pm_sensor_module_time (module_id, recorded_at),
    KEY idx_pm_sensor_device_time (device_id, recorded_at),
    CONSTRAINT fk_pm_sensor_device
        FOREIGN KEY (device_id) REFERENCES pm_devices(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_pm_sensor_module
        FOREIGN KEY (module_id) REFERENCES pm_modules(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS pm_sensor_metrics (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    reading_id BIGINT UNSIGNED NOT NULL,
    device_id BIGINT UNSIGNED NOT NULL,
    module_id BIGINT UNSIGNED NOT NULL,
    recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    metric_key VARCHAR(160) NOT NULL,
    metric_value DOUBLE NOT NULL,
    unit VARCHAR(40) NULL,
    source_key VARCHAR(220) NULL,
    PRIMARY KEY (id),
    KEY idx_pm_metrics_module_key_time (module_id, metric_key, recorded_at),
    KEY idx_pm_metrics_device_time (device_id, recorded_at),
    KEY idx_pm_metrics_reading (reading_id),
    CONSTRAINT fk_pm_metrics_reading
        FOREIGN KEY (reading_id) REFERENCES pm_sensor_readings(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_pm_metrics_device
        FOREIGN KEY (device_id) REFERENCES pm_devices(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_pm_metrics_module
        FOREIGN KEY (module_id) REFERENCES pm_modules(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS pm_diagnostic_snapshots (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    device_id BIGINT UNSIGNED NOT NULL,
    module_id BIGINT UNSIGNED NOT NULL,
    recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    source_recorded_at DATETIME(6) NULL,
    sample_count INT NULL,
    health_score INT NULL,
    condition_state ENUM('NORMAL', 'WATCH', 'WARNING', 'MAINTENANCE_REQUIRED') NOT NULL DEFAULT 'NORMAL',
    temperature_c DOUBLE NULL,
    temperature_avg_c DOUBLE NULL,
    temperature_trend_c_per_min DOUBLE NULL,
    pressure_kpa DOUBLE NULL,
    pressure_avg_kpa DOUBLE NULL,
    current_a DOUBLE NULL,
    current_avg_a DOUBLE NULL,
    vibration DOUBLE NULL,
    vibration_avg DOUBLE NULL,
    ai_model_version VARCHAR(80) NULL,
    ai_condition VARCHAR(80) NULL,
    ai_confidence DOUBLE NULL,
    ai_notes TEXT NULL,
    PRIMARY KEY (id),
    KEY idx_pm_diag_module_time (module_id, recorded_at),
    KEY idx_pm_diag_time_module (recorded_at, module_id),
    KEY idx_pm_diag_device_time (device_id, recorded_at),
    KEY idx_pm_diag_condition (condition_state),
    CONSTRAINT fk_pm_diag_device
        FOREIGN KEY (device_id) REFERENCES pm_devices(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_pm_diag_module
        FOREIGN KEY (module_id) REFERENCES pm_modules(id)
        ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS pm_alerts (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    device_id BIGINT UNSIGNED NOT NULL,
    module_id BIGINT UNSIGNED NOT NULL,
    diagnostic_id BIGINT UNSIGNED NULL,
    issue_key VARCHAR(160) NOT NULL DEFAULT 'diagnostic_alert',
    severity ENUM('info', 'warning', 'critical') NOT NULL DEFAULT 'info',
    title VARCHAR(220) NOT NULL,
    message TEXT NULL,
    acknowledged TINYINT(1) NOT NULL DEFAULT 0,
    acknowledged_by BIGINT UNSIGNED NULL,
    acknowledged_at DATETIME NULL,
    suppressed_until DATETIME NULL,
    recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_pm_alerts_module_time (module_id, recorded_at),
    KEY idx_pm_alerts_issue_time (device_id, module_id, issue_key, recorded_at),
    KEY idx_pm_alerts_suppression (module_id, issue_key, suppressed_until),
    KEY idx_pm_alerts_severity (severity),
    CONSTRAINT fk_pm_alerts_device
        FOREIGN KEY (device_id) REFERENCES pm_devices(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_pm_alerts_module
        FOREIGN KEY (module_id) REFERENCES pm_modules(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_pm_alerts_diag
        FOREIGN KEY (diagnostic_id) REFERENCES pm_diagnostic_snapshots(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_pm_alerts_ack_user
        FOREIGN KEY (acknowledged_by) REFERENCES pm_users(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS pm_work_orders (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    device_id BIGINT UNSIGNED NOT NULL,
    module_id BIGINT UNSIGNED NULL,
    title VARCHAR(220) NOT NULL,
    description TEXT NULL,
    priority ENUM('LOW', 'MEDIUM', 'HIGH', 'CRITICAL') NOT NULL DEFAULT 'MEDIUM',
    status ENUM('OPEN', 'IN_PROGRESS', 'DONE', 'CANCELLED') NOT NULL DEFAULT 'OPEN',
    assigned_to BIGINT UNSIGNED NULL,
    created_by BIGINT UNSIGNED NULL,
    source_alert_id BIGINT UNSIGNED NULL,
    alert_recorded_at DATETIME NULL,
    report_origin VARCHAR(32) NULL,
    event_started_at DATETIME(6) NULL,
    event_ended_at DATETIME(6) NULL,
    event_timezone VARCHAR(64) NULL,
    event_time_precision VARCHAR(16) NOT NULL DEFAULT 'UNKNOWN',
    due_at DATETIME NULL,
    completed_at DATETIME NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_pm_work_status (status),
    KEY idx_pm_work_assigned (assigned_to),
    UNIQUE KEY uq_pm_work_source_alert (source_alert_id),
    CONSTRAINT fk_pm_work_device
        FOREIGN KEY (device_id) REFERENCES pm_devices(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_pm_work_module
        FOREIGN KEY (module_id) REFERENCES pm_modules(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_pm_work_assigned
        FOREIGN KEY (assigned_to) REFERENCES pm_users(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_pm_work_created
        FOREIGN KEY (created_by) REFERENCES pm_users(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_pm_work_source_alert
        FOREIGN KEY (source_alert_id) REFERENCES pm_alerts(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS pm_maintenance_logs (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    device_id BIGINT UNSIGNED NOT NULL,
    module_id BIGINT UNSIGNED NULL,
    work_order_id BIGINT UNSIGNED NULL,
    technician_id BIGINT UNSIGNED NULL,
    technician_name VARCHAR(160) NOT NULL,
    action_taken TEXT NOT NULL,
    parts_used VARCHAR(220) NULL,
    parts_json JSON NULL,
    incident_context_json JSON NULL,
    other_cost_baht DECIMAL(12,2) NOT NULL DEFAULT 0,
    cost_baht DOUBLE NOT NULL DEFAULT 0,
    recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_pm_logs_recorded (recorded_at),
    KEY idx_pm_logs_device (device_id),
    CONSTRAINT fk_pm_logs_device
        FOREIGN KEY (device_id) REFERENCES pm_devices(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_pm_logs_module
        FOREIGN KEY (module_id) REFERENCES pm_modules(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_pm_logs_work
        FOREIGN KEY (work_order_id) REFERENCES pm_work_orders(id)
        ON DELETE SET NULL,
    CONSTRAINT fk_pm_logs_technician
        FOREIGN KEY (technician_id) REFERENCES pm_users(id)
        ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS pm_deletion_audit (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    entity_type ENUM('MAINTENANCE_LOG','WORK_ORDER') NOT NULL,
    entity_id BIGINT UNSIGNED NOT NULL,
    actor_user_id BIGINT UNSIGNED NOT NULL,
    actor_username VARCHAR(160) NOT NULL,
    snapshot_json JSON NOT NULL,
    deleted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    KEY idx_pm_audit_entity (entity_type, entity_id),
    KEY idx_pm_audit_time (deleted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SELECT 'ADI HT9046 pm_* schema is ready' AS result;
