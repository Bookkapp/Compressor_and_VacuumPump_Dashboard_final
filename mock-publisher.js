// Optional mock publisher.
// Run with: node mock-publisher.js
// Env options: HOST=localhost PORT=5001 DEVICE_ID=ESP32-MOCK-001 RATE_HZ=50 node mock-publisher.js

const http = require('http');

const HOST = process.env.HOST || 'localhost';
const PORT = Number(process.env.PORT || 5001);
const DEVICE_ID = process.env.DEVICE_ID || 'ESP32-MOCK-001';
const RATE_HZ = Number(process.env.RATE_HZ || 50);

let t = 0;

function noise(scale) {
  return (Math.random() - 0.5) * scale;
}

function post(payload) {
  const data = Buffer.from(JSON.stringify(payload));
  const req = http.request({
    hostname: HOST,
    port: PORT,
    path: '/api/data',
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Content-Length': data.length
    }
  }, res => res.resume());

  req.on('error', err => console.error(err.message));
  req.write(data);
  req.end();
}

setInterval(() => {
  t += 1 / RATE_HZ;
  const vib = 0.3 * Math.sin(2 * Math.PI * 16 * t) + 0.12 * Math.sin(2 * Math.PI * 32 * t);

  post({
    deviceId: DEVICE_ID,
    machine_name: 'Mock Compressor',
    timestamp: new Date().toISOString(),
    temperature: 43 + 2 * Math.sin(t / 12) + noise(0.2),
    current: 6.7 + 0.9 * Math.sin(t / 4) + noise(0.25),
    accel: {
      x: vib + noise(0.03),
      y: 0.7 * vib + noise(0.03),
      z: 1 + 0.4 * vib + noise(0.02)
    },
    gyro: {
      x: 1.5 * Math.sin(t / 3) + noise(0.25),
      y: 1.2 * Math.cos(t / 4) + noise(0.25),
      z: 0.8 * Math.sin(t / 5) + noise(0.25)
    }
  });
}, 1000 / RATE_HZ);

console.log(`Publishing ${DEVICE_ID} to http://${HOST}:${PORT}/api/data at ${RATE_HZ} Hz`);
