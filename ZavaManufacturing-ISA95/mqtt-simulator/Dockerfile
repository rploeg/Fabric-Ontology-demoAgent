FROM python:3.12.11-slim

LABEL maintainer="Zava Manufacturing" \
      description="MQTT Simulator for Zava factory telemetry"

WORKDIR /app

# Install dependencies first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ src/
COPY simulator-config.yaml .

# Default config path (overridable via ConfigMap mount)
ENV SIMULATOR_CONFIG="/etc/simulator/simulator-config.yaml"

# Run as non-root
RUN useradd --create-home appuser
USER appuser

# D4: basic health check — verify the Python process is alive
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD python -c "import os, signal; os.kill(1, 0)" || exit 1

ENTRYPOINT ["python", "-m", "src.main"]
# K8s: mount ConfigMap to /etc/simulator/simulator-config.yaml (searched first)
# Standalone: falls back to /app/simulator-config.yaml (baked in)
CMD []
