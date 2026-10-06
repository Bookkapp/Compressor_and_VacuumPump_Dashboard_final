#include <Arduino.h>
#include <Wire.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include "EmonLib.h"
#include <WiFi.h>
#include <PubSubClient.h>

// ==========================================
// Network and MQTT Server Config
// ==========================================
const char* ssid = "YOUR_WIFI_SSID";
#ifndef WIFI_PASSWORD
#define WIFI_PASSWORD ""
#endif
const char* password = WIFI_PASSWORD;

// Local PC IPv4 while testing. For production, point this to the MQTT broker IP.
const char* mqttServer = "192.168.1.100";
const uint16_t mqttPort = 1883;

// Keep this unique per ESP32 and avoid "/" in the ID.
const char* deviceId = "ESP32-HT9046-31";
const char* machineCode = "HT9046-31";
const char* moduleCode = "vacuum-pump";
const char* moduleName = "Vacuum Pump";
const char* telemetryTopic = "adi/telemetry";

WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);

// ==========================================
// Physical Sensor Configurations
// ==========================================
const uint8_t ONE_WIRE_BUS = 4;
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);

const int MPU_ADDR = 0x68;

EnergyMonitor emon1;
const int ADC_PIN = 34;

bool isSensorConnected(int pin);
void ensureWifi();
void ensureMqtt();
void publishTelemetry(
    float liveTemp,
    float livePressure,
    double liveCurrent,
    float liveAx,
    float liveAy,
    float liveAz,
    float liveVib
);

void setup() {
    Serial.begin(115200);
    delay(1000);
    Serial.println("\n=== Initializing ADI HT9046 Edge Node ===");

    mqttClient.setServer(mqttServer, mqttPort);
    ensureWifi();

    sensors.begin();
    if (sensors.getDeviceCount() == 0) {
        Serial.println("[DS18B20] Warning: no devices found.");
    } else {
        Serial.print("[DS18B20] Found devices: ");
        Serial.println(sensors.getDeviceCount());
    }

    Wire.begin(21, 22);
    Wire.beginTransmission(MPU_ADDR);
    Wire.write(0x6B);
    Wire.write(0);
    byte error = Wire.endTransmission();

    if (error == 0) {
        Serial.println("[GY-91] MPU9250 detected.");
    } else {
        Serial.println("[GY-91] Sensor not found over I2C.");
    }

    if (isSensorConnected(ADC_PIN)) {
        Serial.println("[Current] Sensor detected.");
    } else {
        Serial.println("[Current] No sensor detected on boot.");
    }
    emon1.current(ADC_PIN, 111.1);

    Serial.println("========================================\n");
}

void loop() {
    ensureWifi();
    ensureMqtt();

    sensors.requestTemperatures();
    float liveTemp = sensors.getTempCByIndex(0);
    if (liveTemp == DEVICE_DISCONNECTED_C) {
        liveTemp = 0.0;
    }

    float liveAx = 0.0, liveAy = 0.0, liveAz = 0.0;
    Wire.beginTransmission(MPU_ADDR);
    Wire.write(0x3B);
    Wire.endTransmission(false);
    Wire.requestFrom(MPU_ADDR, 6, true);

    if (Wire.available() >= 6) {
        int16_t rawX = (Wire.read() << 8) | Wire.read();
        int16_t rawY = (Wire.read() << 8) | Wire.read();
        int16_t rawZ = (Wire.read() << 8) | Wire.read();

        liveAx = rawX / 16384.0;
        liveAy = rawY / 16384.0;
        liveAz = rawZ / 16384.0;
    }

    double Irms_raw = emon1.calcIrms(1480);
    double liveCurrent = (0.0234 * Irms_raw) + 0.3516;
    if (liveCurrent < 0.36) {
        liveCurrent = 0.0;
    }

    float liveVib = sqrt((liveAx * liveAx) + (liveAy * liveAy) + (liveAz * liveAz));
    float livePressure = -77.5;

    publishTelemetry(liveTemp, livePressure, liveCurrent, liveAx, liveAy, liveAz, liveVib);
    mqttClient.loop();
    delay(3000);
}

void ensureWifi() {
    if (WiFi.status() == WL_CONNECTED) {
        return;
    }

    Serial.print("Connecting to Wi-Fi: ");
    Serial.println(ssid);
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid, password);

    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }

    Serial.println("\nWi-Fi connected.");
    Serial.print("Node IP: ");
    Serial.println(WiFi.localIP());
}

void ensureMqtt() {
    if (mqttClient.connected()) {
        return;
    }

    while (!mqttClient.connected()) {
        String clientId = String("adi-esp32-") + deviceId + "-" + String((uint32_t)ESP.getEfuseMac(), HEX);
        Serial.print("Connecting MQTT ");
        Serial.print(mqttServer);
        Serial.print(":");
        Serial.println(mqttPort);

        if (mqttClient.connect(clientId.c_str())) {
            Serial.println("MQTT connected.");
            char statusTopic[96];
            snprintf(statusTopic, sizeof(statusTopic), "adi/status/%s", deviceId);
            mqttClient.publish(statusTopic, "online", true);
        } else {
            Serial.print("MQTT failed. State: ");
            Serial.println(mqttClient.state());
            delay(2000);
        }
    }
}

void publishTelemetry(
    float liveTemp,
    float livePressure,
    double liveCurrent,
    float liveAx,
    float liveAy,
    float liveAz,
    float liveVib
) {
    char jsonPayload[512];
    snprintf(
        jsonPayload,
        sizeof(jsonPayload),
        "{\"device_id\":\"%s\",\"machine_code\":\"%s\",\"module_code\":\"%s\",\"module_name\":\"%s\",\"temperature\":%.2f,\"pressure\":%.2f,\"current\":%.4f,\"ax\":%.4f,\"ay\":%.4f,\"az\":%.4f,\"vibration\":%.4f}",
        deviceId,
        machineCode,
        moduleCode,
        moduleName,
        liveTemp,
        livePressure,
        liveCurrent,
        liveAx,
        liveAy,
        liveAz,
        liveVib
    );

    Serial.println("\nPublishing telemetry:");
    Serial.println(telemetryTopic);
    Serial.println(jsonPayload);

    bool ok = mqttClient.publish(telemetryTopic, jsonPayload);
    Serial.println(ok ? "MQTT publish ok." : "MQTT publish failed.");
}

bool isSensorConnected(int pin) {
    const int numSamples = 100;
    long sum = 0;
    int minVal = 4095;
    int maxVal = 0;

    for (int i = 0; i < numSamples; i++) {
        int val = analogRead(pin);
        sum += val;
        if (val < minVal) minVal = val;
        if (val > maxVal) maxVal = val;
        delay(2);
    }

    int average = sum / numSamples;
    int variance = maxVal - minVal;

    if (average < 200 || average > 3900) return false;
    if (variance > 1500) return false;

    return true;
}
