# Zava Manufacturing — Quick Start (Offline)

Everything runs locally — no internet required.

## 1. Start the MQTT Broker

```bash
/opt/homebrew/opt/mosquitto/sbin/mosquitto -v -c /opt/homebrew/etc/mosquitto/mosquitto.conf
```

Or as a background service:

```bash
brew services start mosquitto
```

## 2. Start the Simulator

```bash
docker run --rm --name zava-sim-test \
  --add-host=host.docker.internal:host-gateway \
  zava-simulator:latest --config /app/simulator-config.yaml
```

## 3. Start the Dashboard

```bash
cd ZavaManufacturing-ISA95/simulator-dashboard
source ../../.venv/bin/activate
python app.py
```

Open **http://localhost:8000**

## Stop Everything

```bash
# Stop simulator
docker stop zava-sim-test

# Stop dashboard
# Ctrl+C in the terminal running app.py

# Stop broker
brew services stop mosquitto
# or Ctrl+C if running in foreground
```
