# Wi-Fi Room Sensor Display (CircuitPython)

A compact Wi-Fi temperature & humidity display built with **CircuitPython**.  
Displays live readings, fetches time from the web, and can send data to **InfluxDB**.

![screenshot placeholder](https://github.com/cr0m/esp32-s2-cp-htu31d-sht4x-influxdb-data-logger/blob/main/image.jpg)
---

## ✨ Features
- 🌡️ HTU31D/SHT4X temperature & humidity sensor (I²C)
- 📊 InfluxDB telemetry output
- 🕒 Periodic time updates from a web API (default 60 sec)
- 📡 Wi-Fi server with simple HTTP server on port 80 (for Dashy uptime reporting)
- 🔘 Button controls for:
  - Toggle sending data (ON/OFF)
  - Adjust brightness
  - Cycle display between Room / IP / Wi-Fi signal


---

## ⚙️ Hardware
| Component | Description |
|------------|--------------|
| ESP32-S2 / ESP32-S3 | CircuitPython board with built-in display |
| HTU31D / SHT4X Sensors | Temperature & humidity (I²C) |
| Buttons | D0, D1, D2 digital inputs |

---

## 🚀 Setup

1. Copy all project files to your CircuitPython device.
2. Create a `secrets.py` file with your network and API details:

```python
secrets = {
    "ssid": "WiFi",
    "password": "Pass",
    "sensor_room": "Office",
    "sensor_host": "sensor-office",
    "influx_url": "http://influx",
    "influx_token": "...",
    "influx_org": "...",
    "influx_bucket": "...",
    "time_server": "http://time-api"
}
```
> ⚠️ Do **not** commit `secrets.py` to GitHub.

3. Reboot your device. You should see live temperature, humidity, and network info.

---

## 🎛️ Controls
| Button | Function |
|--------|-----------|
| **D0** | Toggle data sending ON/OFF  |
| **D1** | Cycle display brightness / turn off screen |
| **D2** | Cycle bottom label: Room → IP → Wi-Fi bars / dBi |

---

## 📤 InfluxDB Output Example
```
temperature,host=...,room=... value=72.3
humidity,host=...,room=... value=35.2
```

---

## 🖋️ Font License

This project includes **League Spartan Bold**, licensed under the **SIL Open Font License 1.1**.  
See [`fonts/OFL.txt`](fonts/OFL.txt) for details.

---

## 🪪 License

This project is licensed under the **MIT License**.  
Feel free to fork, modify, and use it in your own builds.


