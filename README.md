# Belt ML Runtime

Real-time **Remaining Useful Life (RUL)** prediction runtime for conveyor belts. This system leverages **Kafka** for data ingestion, **Numaflow** for stream processing, and the **ELK stack** for observability and visualization.

---

## 🚀 Quick Links

| Link | Description |
|------|-------------|
| [**Installation Guide**](./docs/INSTALLATION.md) | Full step-by-step setup for a fresh system |
| [**System Architecture**](./docs/ARCHITECTURE.md) | Deep dive into components and data flow |
| [**Pipeline Documentation**](./docs/PIPELINE.md) | Numaflow vertex details and scaling |

---

## 🏗️ Architecture at a Glance

The system is designed to run on Kubernetes (Minikube for local development).

```
IoT Sensors
    │
    ▼
[Kafka Topic: belt-iot-data]
    │
    ▼
[Numaflow Pipeline]
    ├── source-transformer  → Deserializes & validates raw messages
    └── ml-runtime (UDF)   → Feature engineering + RUL prediction
    │
    ▼
[Kafka Topic: belt-predictions]
    │
    ▼
[Logstash] → [Elasticsearch] → [Kibana Dashboard]
```

1. **Ingestion** — Sensors push telemetry data to a **Kafka** topic.
2. **Processing** — A **Numaflow** pipeline consumes the stream and routes it through the **ML Runtime UDF**.
3. **Inference** — The Python UDF engineers features and predicts RUL using pre-trained scikit-learn models.
4. **Storage** — Predictions are forwarded to a second Kafka topic, consumed by **Logstash**, and indexed in **Elasticsearch**.
5. **Visualization** — **Kibana** provides real-time belt health dashboards.

---

## � Project Structure

```
belt-ml-runtime/
│
├── app/                          # Core Python application logic
│   ├── main.py                   # Entry point (used for local testing)
│   ├── udf_entry.py              # Numaflow UDF handler (Kafka → prediction)
│   ├── runtime.py                # Prediction orchestration logic
│   ├── feature_engineering.py    # Rolling-window feature computation
│   ├── inference_engine.py       # scikit-learn model inference wrapper
│   ├── source_transformer.py     # Raw message deserialization for Numaflow
│   ├── state_manager.py          # Last-seen state tracking per belt
│   ├── alert_engine.py           # Threshold-based alerting logic
│   ├── config_loader.py          # Loads model_config.json / thresholds.json
│   └── iot_gateway.py            # Simulated IoT data gateway helper
│
├── deploy/                       # Kubernetes manifests
│   ├── kafka-simple.yaml         # Kafka broker (single-node)
│   ├── kafka.yaml                # Kafka (multi-broker / Strimzi)
│   ├── zookeeper.yaml            # Zookeeper for Kafka coordination
│   ├── elasticsearch.yaml        # Elasticsearch deployment & service
│   ├── kibana.yaml               # Kibana deployment & service
│   ├── logstash.yaml             # Logstash pipeline (Kafka → Elasticsearch)
│   ├── isb.yaml                  # Numaflow Inter-Step Buffer (ISB) definition
│   └── belt-pipeline.yaml        # Numaflow pipeline manifest
│
├── docs/                         # In-depth documentation
│   ├── INSTALLATION.md           # New-system setup guide (Minikube, Docker, etc.)
│   ├── ARCHITECTURE.md           # Component diagram and data flow details
│   └── PIPELINE.md               # Numaflow vertex & scaling reference
│
├── model/                        # Pre-trained ML models and configuration
│   ├── belt_rul_model_rul.pkl    # scikit-learn RUL regression model
│   ├── belt_rul_model_health.pkl # scikit-learn health classification model
│   ├── model_config.json         # Feature list, scaler params, model metadata
│   ├── thresholds.json           # Per-belt RUL alert thresholds
│   └── belts_metadata.json       # Belt IDs and metadata mapping
│
├── scripts/                      # Operational / utility scripts
│   ├── delta_catchup.py          # Re-indexes historical data into Elasticsearch
│   ├── setup_kibana.py           # Auto-creates Kibana index patterns & dashboards
│   └── traffic_generator.py      # Generates simulated IoT sensor traffic
│
├── belt-stream-pipeline.yaml     # Top-level Numaflow pipeline spec
├── start-all.ps1                 # One-shot PowerShell startup script
├── Dockerfile                    # Container image for the ML Runtime UDF
├── requirements.txt              # Python dependencies
└── .gitignore                    # Git ignore rules
```

---

## 💻 New System Setup (From Scratch)

> Follow this section when setting up on a **brand new Windows machine**. If tools are already installed, jump to [Getting Started](#-getting-started-local-setup).

### Step 1 — Install Core Tools via Chocolatey

Open **PowerShell as Administrator** and run:

```powershell
# 1. Install Chocolatey package manager
Set-ExecutionPolicy Bypass -Scope Process -Force
[System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072
iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# 2. Install required tools
choco install git -y                  # Git version control
choco install python --version=3.11.0 -y  # Python 3.11
choco install minikube -y             # Local Kubernetes cluster
choco install kubernetes-cli -y       # kubectl — K8s CLI
choco install helm -y                 # Helm — K8s package manager

# 3. Verify installs
git --version
python --version
minikube version
kubectl version --client
helm version
```

### Step 2 — Install Docker Desktop

Minikube uses Docker as its container driver.

1. Download [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/).
2. During install, select **"Use WSL 2 instead of Hyper-V"**.
3. Restart your machine if prompted.
4. Open Docker Desktop and wait until it shows **"Running"** in the system tray.

> **Tip**: Make sure Virtualization is **Enabled** in your BIOS/UEFI before starting.

### Step 3 — Start Minikube

```powershell
# Start Minikube with enough resources for the full stack
minikube start --memory=6144 --cpus=3 --driver=docker

# Enable useful addons
minikube addons enable dashboard
minikube addons enable metrics-server

# Verify the node is Ready
kubectl get nodes
```

Expected output:

```
NAME       STATUS   ROLES           AGE   VERSION
minikube   Ready    control-plane   1m    v1.xx.x
```

### Step 4 — Install Numaflow

```powershell
# Install Numaflow controller and CRDs
kubectl create namespace numaflow-system
kubectl apply -n numaflow-system -f https://raw.githubusercontent.com/numaproj/numaflow/stable/config/install.yaml

# Install the Inter-Step Buffer (NATS JetStream)
kubectl apply -f deploy/isb.yaml
```

### Step 5 — Install Python Dependencies

```powershell
# From the project root
pip install -r requirements.txt
```

---

## 🛠️ Getting Started (Local Setup)

If Minikube, Docker, and all tools are already installed, follow these steps.

### 1. Clone the Repository

```bash
git clone https://github.com/mr-mandeeprana/belt-ml-runtime.git
cd belt-ml-runtime
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the Full Stack

Run the automated startup script (handles everything end-to-end):

```powershell
.\start-all.ps1
```

**This script will:**

- Start Minikube
- Install Numaflow and the ISB
- Build the ML Runtime Docker image inside Minikube
- Deploy Kafka, Zookeeper, Elasticsearch, Kibana, Logstash, and the Numaflow Pipeline
- Set up port-forwards and open Kibana in your browser

---

## 🔧 Operational Commands

### View ML Runtime Logs

```powershell
kubectl logs -l numaflow.numaproj.io/vertex-name=ml-runtime -c main -f
```

### Check All Pod Status

```powershell
kubectl get pods -A
```

### Rebuild & Redeploy ML Runtime Image

```powershell
# Build the Docker image inside Minikube's Docker daemon
& minikube -p minikube docker-env --shell powershell | Invoke-Expression
docker build -t belt-ml-runtime:latest .

# Restart the pipeline to pick up new image
kubectl rollout restart deployment/belt-ml-runtime
```

### Generate Simulated Sensor Traffic

```powershell
python scripts/traffic_generator.py
```

### Run Delta Catchup (Re-index Historical Data)

```powershell
python scripts/delta_catchup.py
```

### Access Dashboards

| Dashboard | URL | Credentials |
|-----------|-----|-------------|
| Kibana | [http://localhost:5601](http://localhost:5601) | — |
| Numaflow UX | [https://localhost:8443](https://localhost:8443) | `admin` / `admin` |
| Minikube Dashboard | Run `minikube dashboard` | — |

---

## 🧹 Teardown

```powershell
# Stop all port-forwards and delete the stack
kubectl delete -f belt-stream-pipeline.yaml
kubectl delete -f deploy/

# Stop Minikube (keeps cluster state)
minikube stop

# Delete Minikube cluster entirely (clean slate)
minikube delete
```

---

## 📜 License

Internal / Proprietary
