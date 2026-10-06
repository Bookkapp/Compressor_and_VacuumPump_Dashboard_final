-- ============================================================
-- Local mockup: Vacuum Pump source database
-- ============================================================
CREATE DATABASE IF NOT EXISTS vacuum_pump_db
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE vacuum_pump_db;

CREATE TABLE IF NOT EXISTS vacuum_pump_readings (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    devices_id VARCHAR(60) NOT NULL,
    recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    temperature DOUBLE NULL,
    accel_x DOUBLE NULL,
    accel_y DOUBLE NULL,
    accel_z DOUBLE NULL,
    vibration DOUBLE NULL,
    current_amp DOUBLE NULL,
    PRIMARY KEY (id),
    KEY idx_vp_device_time (devices_id, recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Seed: Vacuum Pump device "VP001" — 60 readings over the last hour
DELETE FROM vacuum_pump_readings WHERE devices_id = 'VP001';

INSERT INTO vacuum_pump_readings (devices_id, recorded_at, temperature, accel_x, accel_y, accel_z, vibration, current_amp)
WITH RECURSIVE seq AS (
    SELECT 0 AS n
    UNION ALL
    SELECT n + 1 FROM seq WHERE n < 59
)
SELECT
    'VP001',
    DATE_SUB(NOW(), INTERVAL (59 - n) MINUTE),
    ROUND(42.0 + (RAND() * 6), 2),
    ROUND(0.02 + (RAND() * 0.08), 4),
    ROUND(0.01 + (RAND() * 0.06), 4),
    ROUND(9.75 + (RAND() * 0.15), 4),
    ROUND(0.3 + (RAND() * 0.5), 4),
    ROUND(2.5 + (RAND() * 1.2), 3)
FROM seq;

-- ============================================================
-- Local mockup: Compressor source database (HT9046MX)
-- ============================================================
CREATE DATABASE IF NOT EXISTS ht9046mx_iot
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE ht9046mx_iot;

CREATE TABLE IF NOT EXISTS ht9046mx_readings (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    machine_number VARCHAR(60) NOT NULL,
    recorded_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    Status VARCHAR(40) NULL,
    -- Module 1
    Hp_1st_1 DOUBLE NULL, Lp_1st_1 DOUBLE NULL,
    Hp_2nd_1 DOUBLE NULL, Lp_2nd_1 DOUBLE NULL,
    Valve_1 DOUBLE NULL, TempHi_1 DOUBLE NULL, TempLo_1 DOUBLE NULL,
    Status_1 DOUBLE NULL, Busy_1 DOUBLE NULL, SV_1 DOUBLE NULL,
    -- Module 2
    Hp_1st_2 DOUBLE NULL, Lp_1st_2 DOUBLE NULL,
    Hp_2nd_2 DOUBLE NULL, Lp_2nd_2 DOUBLE NULL,
    Valve_2 DOUBLE NULL, TempHi_2 DOUBLE NULL, TempLo_2 DOUBLE NULL,
    Status_2 DOUBLE NULL, Busy_2 DOUBLE NULL, SV_2 DOUBLE NULL,
    -- Module 3
    Hp_1st_3 DOUBLE NULL, Lp_1st_3 DOUBLE NULL,
    Hp_2nd_3 DOUBLE NULL, Lp_2nd_3 DOUBLE NULL,
    Valve_3 DOUBLE NULL, TempHi_3 DOUBLE NULL, TempLo_3 DOUBLE NULL,
    Status_3 DOUBLE NULL, Busy_3 DOUBLE NULL, SV_3 DOUBLE NULL,
    -- Module 4
    Hp_1st_4 DOUBLE NULL, Lp_1st_4 DOUBLE NULL,
    Hp_2nd_4 DOUBLE NULL, Lp_2nd_4 DOUBLE NULL,
    Valve_4 DOUBLE NULL, TempHi_4 DOUBLE NULL, TempLo_4 DOUBLE NULL,
    Status_4 DOUBLE NULL, Busy_4 DOUBLE NULL, SV_4 DOUBLE NULL,
    -- Module 5
    Hp_1st_5 DOUBLE NULL, Lp_1st_5 DOUBLE NULL,
    Hp_2nd_5 DOUBLE NULL, Lp_2nd_5 DOUBLE NULL,
    Valve_5 DOUBLE NULL, TempHi_5 DOUBLE NULL, TempLo_5 DOUBLE NULL,
    Status_5 DOUBLE NULL, Busy_5 DOUBLE NULL, SV_5 DOUBLE NULL,
    -- Module 6
    Hp_1st_6 DOUBLE NULL, Lp_1st_6 DOUBLE NULL,
    Hp_2nd_6 DOUBLE NULL, Lp_2nd_6 DOUBLE NULL,
    Valve_6 DOUBLE NULL, TempHi_6 DOUBLE NULL, TempLo_6 DOUBLE NULL,
    Status_6 DOUBLE NULL, Busy_6 DOUBLE NULL, SV_6 DOUBLE NULL,
    -- Module 7
    Hp_1st_7 DOUBLE NULL, Lp_1st_7 DOUBLE NULL,
    Hp_2nd_7 DOUBLE NULL, Lp_2nd_7 DOUBLE NULL,
    Valve_7 DOUBLE NULL, TempHi_7 DOUBLE NULL, TempLo_7 DOUBLE NULL,
    Status_7 DOUBLE NULL, Busy_7 DOUBLE NULL, SV_7 DOUBLE NULL,
    -- Module 8
    Hp_1st_8 DOUBLE NULL, Lp_1st_8 DOUBLE NULL,
    Hp_2nd_8 DOUBLE NULL, Lp_2nd_8 DOUBLE NULL,
    Valve_8 DOUBLE NULL, TempHi_8 DOUBLE NULL, TempLo_8 DOUBLE NULL,
    Status_8 DOUBLE NULL, Busy_8 DOUBLE NULL, SV_8 DOUBLE NULL,
    PRIMARY KEY (id),
    KEY idx_comp_machine_time (machine_number, recorded_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Seed: Compressor machine "MX001" — 60 readings over the last hour
-- All 8 modules with realistic pressure/temp values
DELETE FROM ht9046mx_readings WHERE machine_number = 'MX001';

INSERT INTO ht9046mx_readings (
    machine_number, recorded_at, Status,
    Hp_1st_1, Lp_1st_1, Hp_2nd_1, Lp_2nd_1, Valve_1, TempHi_1, TempLo_1, Status_1, Busy_1, SV_1,
    Hp_1st_2, Lp_1st_2, Hp_2nd_2, Lp_2nd_2, Valve_2, TempHi_2, TempLo_2, Status_2, Busy_2, SV_2,
    Hp_1st_3, Lp_1st_3, Hp_2nd_3, Lp_2nd_3, Valve_3, TempHi_3, TempLo_3, Status_3, Busy_3, SV_3,
    Hp_1st_4, Lp_1st_4, Hp_2nd_4, Lp_2nd_4, Valve_4, TempHi_4, TempLo_4, Status_4, Busy_4, SV_4,
    Hp_1st_5, Lp_1st_5, Hp_2nd_5, Lp_2nd_5, Valve_5, TempHi_5, TempLo_5, Status_5, Busy_5, SV_5,
    Hp_1st_6, Lp_1st_6, Hp_2nd_6, Lp_2nd_6, Valve_6, TempHi_6, TempLo_6, Status_6, Busy_6, SV_6,
    Hp_1st_7, Lp_1st_7, Hp_2nd_7, Lp_2nd_7, Valve_7, TempHi_7, TempLo_7, Status_7, Busy_7, SV_7,
    Hp_1st_8, Lp_1st_8, Hp_2nd_8, Lp_2nd_8, Valve_8, TempHi_8, TempLo_8, Status_8, Busy_8, SV_8
)
WITH RECURSIVE seq AS (
    SELECT 0 AS n
    UNION ALL
    SELECT n + 1 FROM seq WHERE n < 59
)
SELECT
    'MX001',
    DATE_SUB(NOW(), INTERVAL (59 - n) MINUTE),
    'RUN',
    -- Module 1
    ROUND(145 + RAND()*20, 1), ROUND(35 + RAND()*10, 1),
    ROUND(280 + RAND()*30, 1), ROUND(60 + RAND()*15, 1),
    ROUND(50 + RAND()*30, 0), ROUND(650 + RAND()*60, 1), ROUND(250 + RAND()*40, 1),
    1, ROUND(RAND()), ROUND(40 + RAND()*10, 1),
    -- Module 2
    ROUND(140 + RAND()*25, 1), ROUND(32 + RAND()*12, 1),
    ROUND(275 + RAND()*35, 1), ROUND(58 + RAND()*18, 1),
    ROUND(45 + RAND()*35, 0), ROUND(640 + RAND()*70, 1), ROUND(245 + RAND()*45, 1),
    1, ROUND(RAND()), ROUND(38 + RAND()*12, 1),
    -- Module 3
    ROUND(150 + RAND()*18, 1), ROUND(38 + RAND()*8, 1),
    ROUND(285 + RAND()*25, 1), ROUND(62 + RAND()*12, 1),
    ROUND(55 + RAND()*25, 0), ROUND(660 + RAND()*50, 1), ROUND(255 + RAND()*35, 1),
    1, ROUND(RAND()), ROUND(42 + RAND()*8, 1),
    -- Module 4
    ROUND(142 + RAND()*22, 1), ROUND(33 + RAND()*11, 1),
    ROUND(278 + RAND()*32, 1), ROUND(59 + RAND()*16, 1),
    ROUND(48 + RAND()*32, 0), ROUND(645 + RAND()*65, 1), ROUND(248 + RAND()*42, 1),
    1, ROUND(RAND()), ROUND(39 + RAND()*11, 1),
    -- Module 5
    ROUND(148 + RAND()*20, 1), ROUND(36 + RAND()*10, 1),
    ROUND(282 + RAND()*28, 1), ROUND(61 + RAND()*14, 1),
    ROUND(52 + RAND()*28, 0), ROUND(655 + RAND()*55, 1), ROUND(252 + RAND()*38, 1),
    1, ROUND(RAND()), ROUND(41 + RAND()*9, 1),
    -- Module 6
    ROUND(138 + RAND()*24, 1), ROUND(31 + RAND()*13, 1),
    ROUND(270 + RAND()*38, 1), ROUND(56 + RAND()*20, 1),
    ROUND(42 + RAND()*38, 0), ROUND(635 + RAND()*75, 1), ROUND(240 + RAND()*48, 1),
    1, ROUND(RAND()), ROUND(37 + RAND()*13, 1),
    -- Module 7
    ROUND(146 + RAND()*19, 1), ROUND(37 + RAND()*9, 1),
    ROUND(283 + RAND()*27, 1), ROUND(63 + RAND()*11, 1),
    ROUND(53 + RAND()*27, 0), ROUND(658 + RAND()*52, 1), ROUND(254 + RAND()*36, 1),
    1, ROUND(RAND()), ROUND(43 + RAND()*7, 1),
    -- Module 8
    ROUND(143 + RAND()*21, 1), ROUND(34 + RAND()*10, 1),
    ROUND(277 + RAND()*33, 1), ROUND(58 + RAND()*17, 1),
    ROUND(47 + RAND()*33, 0), ROUND(648 + RAND()*62, 1), ROUND(249 + RAND()*41, 1),
    1, ROUND(RAND()), ROUND(40 + RAND()*10, 1)
FROM seq;

-- ============================================================
-- Dashboard metadata database
-- ============================================================
CREATE DATABASE IF NOT EXISTS predictive_maintenance
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

SELECT 'All mock databases created and seeded!' AS result;
