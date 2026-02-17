# Deploying the Zava MQTT Simulator to Azure IoT Operations (AKS)

This guide walks through deploying the simulator to an AKS cluster running
**Azure IoT Operations (AIO)**, so telemetry flows from the simulator pod →
AIO MQTT broker → AIO Data Processor → Microsoft Fabric Eventhouse.

---

## Architecture

```
┌──────────────────── AKS Cluster ────────────────────────────────┐
│                                                                 │
│  namespace: zava-simulator           namespace: azure-iot-ops   │
│  ┌───────────────────────┐           ┌──────────────────────┐   │
│  │  zava-simulator pod   │──MQTT──▶  │  AIO MQTT Broker     │   │
│  │  (10 streams, 11      │  :1883    │  (aio-broker svc)    │   │
│  │   anomaly scenarios)  │  SAT auth │                      │   │
│  └───────────────────────┘           └──────────┬───────────┘   │
│         ▲ ConfigMap                             │               │
│         │ + SA Token                    Data Processor /        │
│                                        Data Flow pipeline      │
│                                                 │               │
└─────────────────────────────────────────────────┼───────────────┘
                                                  │
                                                  ▼
                                     ┌──────────────────────┐
                                     │  Microsoft Fabric     │
                                     │  Eventhouse (KQL DB)  │
                                     └──────────────────────┘
```

## Prerequisites

| Requirement | Details |
|---|---|
| **Azure subscription** | With permissions to create AKS, ACR, and AIO resources |
| **AKS cluster** | 1.27+ with Azure IoT Operations extension installed |
| **Azure Container Registry (ACR)** | To host the simulator image |
| **Azure CLI** | `az` ≥ 2.55 with `aks`, `acr`, and `iot-ops` extensions |
| **kubectl** | Connected to your AKS cluster |
| **Docker** | For building the container image |

### Verify your tools

```bash
az version          # 2.55+
kubectl version     # connected to the right cluster
az extension list -o table | grep iot-ops
```

---

## Step 1 — Build and push the container image

```bash
# Variables — adjust to your environment
ACR_NAME="myacr"                           # your ACR name (no .azurecr.io)
IMAGE_TAG="zava-simulator:v1.0"

# Build
cd ZavaManufacturing-ISA95/mqtt-simulator
docker build -t "$ACR_NAME.azurecr.io/$IMAGE_TAG" .

# Login to ACR
az acr login --name "$ACR_NAME"

# Push
docker push "$ACR_NAME.azurecr.io/$IMAGE_TAG"
```

### Attach ACR to AKS (if not already done)

```bash
AKS_RG="my-resource-group"
AKS_NAME="my-aks-cluster"

az aks update \
  --resource-group "$AKS_RG" \
  --name "$AKS_NAME" \
  --attach-acr "$ACR_NAME"
```

---

## Step 2 — Prepare the Kubernetes manifests

The manifests are in `k8s/`. Before applying, update the image reference in
the Deployment:

```bash
cd k8s/
```

Edit `deployment.yaml` — set the image to your ACR path:

```yaml
containers:
  - name: simulator
    image: myacr.azurecr.io/zava-simulator:v1.0   # ← your ACR image
    imagePullPolicy: Always
```

### Manifest overview

| File | What it creates |
|------|----------------|
| `namespace.yaml` | `zava-simulator` namespace |
| `service-account.yaml` | ServiceAccount `zava-simulator` with `aio-broker-auth/audience: "aio-internal"` |
| `configmap.yaml` | `zava-simulator-config` ConfigMap with simulator-config.yaml |
| `deployment.yaml` | Deployment with SAT token projection + ConfigMap volume mount |
| `broker-auth.yaml` | BrokerAuthentication + BrokerAuthorization for AIO (apply in `azure-iot-operations` NS) |
| `kustomization.yaml` | Kustomize overlay tying everything together |

### (Optional) Use the full config

The default ConfigMap has a minimal inline config. To use the full
`simulator-config.yaml` with all stream and anomaly settings:

```bash
# Replace the ConfigMap data with the full config file
kubectl create configmap zava-simulator-config \
  --from-file=simulator-config.yaml=../simulator-config.yaml \
  -n zava-simulator \
  --dry-run=client -o yaml > configmap-full.yaml
```

Then replace `configmap.yaml` with `configmap-full.yaml` (or add it to your
Kustomize patches).

---

## Step 3 — Configure the AIO MQTT broker for the simulator

The simulator authenticates to the AIO MQTT broker using a **Service Account
Token (SAT)**. Kubernetes projects a short-lived token into the pod at
`/var/run/secrets/tokens/mqtt-client-token` with audience `aio-internal`.

### 3a. BrokerAuthentication

AIO's default `BrokerAuthentication` resource usually already accepts SAT
tokens. Verify:

```bash
kubectl get brokerauthentication -n azure-iot-operations -o yaml
```

Look for a `serviceAccountToken` method with audience `aio-internal`. If it
doesn't exist, apply the manifest included in this repo:

```bash
kubectl apply -f k8s/broker-auth.yaml
```

This creates both the `BrokerAuthentication` and `BrokerAuthorization`
resources. The manifest is equivalent to:

```yaml
apiVersion: mqttbroker.iotoperations.azure.com/v1
kind: BrokerAuthentication
metadata:
  name: zava-simulator-authn
  namespace: azure-iot-operations
spec:
  authenticationMethods:
    - method: ServiceAccountToken
      serviceAccountTokenSettings:
        audiences:
          - "aio-internal"
```

### 3b. BrokerAuthorization (optional but recommended)

Grant the simulator's ServiceAccount permission to publish and subscribe on
the topics it uses:

```yaml
apiVersion: mqttbroker.iotoperations.azure.com/v1
kind: BrokerAuthorization
metadata:
  name: zava-simulator-authz
  namespace: azure-iot-operations
spec:
  authorizationPolicies:
    rules:
      - principals:
          serviceAccounts:
            - namespace: zava-simulator
              name: zava-simulator
        brokerResources:
          # Allow publishing to all zava topics
          - method: Connect
            topics: []
          - method: Publish
            topics:
              - "zava/#"
          - method: Subscribe
            topics:
              - "zava/simulator/command"
```

> **Tip:** If you use UNS topic mode, the topics follow the pattern
> `zava/{site}/{area}/{line}/{equipment}/telemetry/{stream}`. The wildcard
> `zava/#` covers all of them.

---

## Step 4 — Deploy to AKS

```bash
# From the k8s/ directory
kubectl apply -k .
```

Or apply each manifest individually:

```bash
kubectl apply -f namespace.yaml
kubectl apply -f service-account.yaml
kubectl apply -f configmap.yaml
kubectl apply -f deployment.yaml
```

### Verify the deployment

```bash
# Check the pod is running
kubectl get pods -n zava-simulator

# Watch startup logs
kubectl logs -n zava-simulator -l app=zava-simulator -f

# Expected output:
# INFO  Connected to MQTT broker aio-broker.azure-iot-operations.svc.cluster.local:1883
# INFO  Using Service Account Token authentication
# INFO  Starting equipment_telemetry_stream (interval: 30s)
# INFO  Starting machine_state_telemetry_stream ...
# ...
```

### Verify messages are reaching the AIO broker

From a pod **inside** the cluster (or using `kubectl exec` on the AIO broker):

```bash
# Quick test: exec into a debug pod with mosquitto-clients
kubectl run mqtt-debug --rm -it --image=eclipse-mosquitto:2 \
  -n zava-simulator -- mosquitto_sub \
  -h aio-broker.azure-iot-operations.svc.cluster.local \
  -p 1883 -t 'zava/#' -v --count 5
```

---

## Step 5 — (Alternative) Event Hub output mode on AKS

Instead of using the MQTT broker → Data Flow → Fabric pipeline, the simulator
can publish **directly to Azure Event Hub** using `outputMode: "eventHub"` with
**AKS Workload Identity** (no secrets required).

### 5a. Enable Workload Identity on the service account

```bash
# Get your Event Hub namespace's resource ID
EH_NS_RESOURCE_ID=$(az eventhubs namespace show \
  --resource-group "$RG" --name "$EH_NAMESPACE" --query id -o tsv)

# Create a user-assigned managed identity (or reuse an existing one)
az identity create --name zava-simulator-identity \
  --resource-group "$RG" --location "$LOCATION"

CLIENT_ID=$(az identity show --name zava-simulator-identity \
  --resource-group "$RG" --query clientId -o tsv)
IDENTITY_ID=$(az identity show --name zava-simulator-identity \
  --resource-group "$RG" --query id -o tsv)

# Assign "Azure Event Hubs Data Sender" role
az role assignment create \
  --role "Azure Event Hubs Data Sender" \
  --assignee "$CLIENT_ID" \
  --scope "$EH_NS_RESOURCE_ID"

# Create federated credential for the simulator's K8s service account
AKS_OIDC_ISSUER=$(az aks show --resource-group "$RG" --name "$AKS_NAME" \
  --query "oidcIssuerProfile.issuerUrl" -o tsv)

az identity federated-credential create \
  --name zava-simulator-fed \
  --identity-name zava-simulator-identity \
  --resource-group "$RG" \
  --issuer "$AKS_OIDC_ISSUER" \
  --subject "system:serviceaccount:zava-simulator:zava-simulator" \
  --audiences "api://AzureADTokenExchange"
```

### 5b. Annotate the Kubernetes service account

Add the managed identity client ID to the ServiceAccount:

```yaml
# k8s/service-account.yaml — add:
metadata:
  annotations:
    azure.workload.identity/client-id: "<CLIENT_ID>"  # from step 5a
```

And add the workload identity label to the Deployment pod template:

```yaml
# k8s/deployment.yaml — add to pod template:
metadata:
  labels:
    azure.workload.identity/use: "true"
```

### 5c. Update the ConfigMap for Event Hub

```yaml
outputMode: "eventHub"

eventHub:
  fullyQualifiedNamespace: "<namespace>.servicebus.windows.net"
  eventhubName: "zava-telemetry"
  credential: "managedIdentity"   # uses Workload Identity — zero secrets
  maxBatchSize: 100
  maxWaitTimeSec: 1.0
  partitionKeyMode: "topic"
```

`DefaultAzureCredential` (which `managedIdentity` uses under the hood) will
pick up the Workload Identity token automatically — no connection strings,
environment variables, or secrets needed.

---

## Step 6 — Set up the data pipeline to Fabric Eventhouse

Once messages are flowing into the AIO MQTT broker, configure a **Data Flow**
(or Data Processor pipeline) to route them to Microsoft Fabric.

### 5a. Create an Eventhouse in Fabric

1. In your Fabric workspace, create an **Eventhouse** with a KQL database
   (e.g., `ZavaManufacturing`)
2. Create tables matching the simulator streams. See
   [Bindings/eventhouse-binding.md](../Bindings/eventhouse-binding.md) for the
   recommended schema

### 5b. Create a data connection

In Fabric Eventhouse, create a **data connection** for each stream (or use a
shared one with routing rules):

- **Source type:** Event Hub / MQTT (via AIO Data Flow)
- **Data format:** JSON
- **Mapping:** Map the simulator JSON fields to KQL table columns

### 5c. Configure the AIO Data Flow

Create an AIO Data Flow resource to route MQTT topics to Fabric:

```yaml
apiVersion: connectivity.iotoperations.azure.com/v1
kind: DataFlow
metadata:
  name: zava-to-fabric
  namespace: azure-iot-operations
spec:
  profileRef: default
  operations:
    - operationType: source
      sourceSettings:
        endpointRef: default          # AIO's built-in MQTT endpoint
        dataSources:
          - "zava/+/+/+/+/telemetry/#"   # UNS pattern
          - "zava/telemetry/#"             # flat pattern (if using flat mode)
          - "zava/events/#"
          - "zava/anomalies/#"
    - operationType: destination
      destinationSettings:
        endpointRef: fabric-eventhouse     # your Fabric endpoint reference
        dataDestination: "ZavaManufacturing"
```

You also need a **DataFlowEndpoint** pointing to your Fabric Eventhouse:

```yaml
apiVersion: connectivity.iotoperations.azure.com/v1
kind: DataFlowEndpoint
metadata:
  name: fabric-eventhouse
  namespace: azure-iot-operations
spec:
  endpointType: dataExplorer
  dataExplorerSettings:
    host: "https://<your-eventhouse>.z0.kusto.fabric.microsoft.com"
    database: "ZavaManufacturing"
    authentication:
      method: managedIdentity
      managedIdentitySettings:
        audience: "https://kusto.kusto.windows.net"
```

> **Note:** The exact AIO Data Flow CRD API may vary with your AIO version.
> Check the [Azure IoT Operations documentation](https://learn.microsoft.com/azure/iot-operations/)
> for the latest schema.

---

## Step 7 — Runtime operations

### Send commands to the simulator

The simulator subscribes to `zava/simulator/command` and responds on
`zava/simulator/status`. You can send commands from within the cluster:

```bash
# Get simulator status
kubectl run mqtt-cmd --rm -it --image=eclipse-mosquitto:2 \
  -n zava-simulator -- mosquitto_pub \
  -h aio-broker.azure-iot-operations.svc.cluster.local \
  -p 1883 -t 'zava/simulator/command' \
  -m '{"action":"status"}'
```

See [COMMANDS.md](COMMANDS.md) for the full list of available commands.

### Update configuration at runtime

The simulator watches `simulator-config.yaml` for changes and **automatically
reloads** when the file is modified. On AKS, ConfigMap updates are propagated
to the mounted volume by the kubelet (typically within 30–60 seconds).

```bash
# Update the ConfigMap with a new config
kubectl create configmap zava-simulator-config \
  --from-file=simulator-config.yaml=../simulator-config.yaml \
  -n zava-simulator \
  --dry-run=client -o yaml | kubectl apply -f -

# The simulator detects the change automatically — no restart needed!
# If you need an immediate restart:
kubectl rollout restart deployment/zava-simulator -n zava-simulator
```

The auto-reload covers all config changes: output mode (MQTT ↔ Event Hub),
broker settings, stream enable/disable, intervals, anomaly scenarios, etc.
Signals (SIGINT/SIGTERM) still trigger a normal shutdown without reload.

### Scale (if needed)

The simulator is designed to run as a single replica. Running multiple replicas
would produce duplicate telemetry. If you need higher throughput, increase
`simulation.tickIntervalSec` or reduce per-stream intervals instead.

### View logs

```bash
# Tail logs
kubectl logs -n zava-simulator -l app=zava-simulator -f

# JSON-formatted logs (default in AKS config)
kubectl logs -n zava-simulator -l app=zava-simulator --tail=50 | jq .
```

---

## Configuration reference (AKS vs Local)

| Setting | AKS (in-cluster) | Local (Docker) | Local (no Docker) |
|---------|:-:|:-:|:-:|
| `outputMode` | `mqtt` or `eventHub` | `mqtt` or `eventHub` | `mqtt` or `eventHub` |
| `mqtt.broker` | `aio-broker.azure-iot-operations.svc.cluster.local` | `host.docker.internal` | `localhost` |
| `mqtt.port` | `1883` | `1883` | `1883` |
| `mqtt.authMethod` | `serviceAccountToken` | `usernamePassword` | `usernamePassword` |
| `mqtt.useTls` | `false` *(in-cluster)* | `false` | `false` |
| `eventHub.credential` | `managedIdentity` | `defaultCredential` | `defaultCredential` |
| Event Hub auth source | Workload Identity (auto) | SP env vars (`AZURE_*`) | Azure CLI (`az login`) |
| Config mount | ConfigMap → `/etc/simulator/` | `-v` bind mount or baked-in | `--config ./path` |
| Docker flag | N/A (ACR pull) | `--add-host=host.docker.internal:host-gateway` | N/A |

> **Docker + Event Hub:** Use `defaultCredential` with a service principal.
> Pass `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, and `AZURE_CLIENT_SECRET` via
> `docker run -e` or `--env-file .env`. The SDK's `EnvironmentCredential`
> (first in the `DefaultAzureCredential` chain) picks them up automatically.
> See [.env.example](.env.example) for setup instructions.

---

## Troubleshooting

### Pod stays in CrashLoopBackOff

```bash
kubectl logs -n zava-simulator -l app=zava-simulator --previous
```

Common causes:
- **SAT token not projected** — check the `volumeMounts` and `volumes` in the
  Deployment for the `mqtt-token` projected volume
- **Broker unreachable** — verify the AIO broker service exists:
  `kubectl get svc -n azure-iot-operations | grep broker`
- **Auth rejected** — verify `BrokerAuthentication` accepts audience
  `aio-internal` and the ServiceAccount has the right annotation

### Connection refused / timeout

```bash
# Test in-cluster connectivity
kubectl run mqtt-test --rm -it --image=busybox -n zava-simulator -- \
  nc -zv aio-broker.azure-iot-operations.svc.cluster.local 1883
```

If the port is unreachable, check:
1. The AIO MQTT broker pods are healthy:
   `kubectl get pods -n azure-iot-operations | grep broker`
2. Network policies aren't blocking cross-namespace traffic
3. The broker service is exposed on port 1883:
   `kubectl get svc aio-broker -n azure-iot-operations`

### Messages not reaching Fabric

1. Verify messages arrive at the broker (Step 4 verification)
2. Check the Data Flow status:
   `kubectl get dataflow -n azure-iot-operations`
3. Inspect Data Flow logs:
   `kubectl logs -n azure-iot-operations -l app=dataflow -f`
4. Verify the Fabric Eventhouse data connection is active
5. Check the KQL database for ingested rows:
   ```kql
   EquipmentTelemetry | count
   MachineStateTelemetry | take 5
   ```

### SAT token expired

Kubernetes automatically rotates projected service account tokens. The token
has a 1-hour expiration (`expirationSeconds: 3600` in the Deployment). The
simulator re-reads the token file before every (re)connect attempt via the
`on_pre_connect` callback, so rotated tokens are picked up automatically
without a pod restart.

If you still see auth errors after rotation, verify:
1. The projected volume is correctly mounted at `/var/run/secrets/tokens/`
2. The token audience matches the `BrokerAuthentication` config (`aio-internal`)
3. The kubelet has refreshed the file:
   `kubectl exec -n zava-simulator deploy/zava-simulator -- cat /var/run/secrets/tokens/mqtt-client-token | cut -c1-20`

---

## Cleanup

```bash
# Remove the simulator
kubectl delete -k k8s/

# Or remove individually
kubectl delete namespace zava-simulator

# Remove the BrokerAuthorization rule (if created)
kubectl delete brokerauthorization zava-simulator-authz -n azure-iot-operations

# Remove the ACR image (optional)
az acr repository delete --name "$ACR_NAME" --image "$IMAGE_TAG" --yes
```

---

## Quick reference commands

```bash
# Deploy
kubectl apply -k k8s/

# Check status
kubectl get pods -n zava-simulator
kubectl logs -n zava-simulator -l app=zava-simulator -f

# Update config (auto-reloads — no restart needed)
kubectl create configmap zava-simulator-config \
  --from-file=simulator-config.yaml=../simulator-config.yaml \
  -n zava-simulator --dry-run=client -o yaml | kubectl apply -f -

# Force restart (if needed)
kubectl rollout restart deployment/zava-simulator -n zava-simulator

# Send command
kubectl run mqtt-cmd --rm -it --image=eclipse-mosquitto:2 -n zava-simulator \
  -- mosquitto_pub -h aio-broker.azure-iot-operations.svc.cluster.local \
  -p 1883 -t 'zava/simulator/command' -m '{"action":"status"}'

# Tear down
kubectl delete -k k8s/
```
