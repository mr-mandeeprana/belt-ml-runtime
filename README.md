# Belt ML Runtime

Real-time Remaining Useful Life (RUL) prediction runtime for conveyor belts. This system leverages Kafka for data ingestion, Numaflow for stream processing, and the ELK stack for observability.

## 🚀 Quick Links

- [**Detailed Installation Guide**](./docs/INSTALLATION.md) - How to set up Minikube and tools on a new system.
- [**System Architecture**](./docs/ARCHITECTURE.md) - Deep dive into components and data flow.
- [**Pipeline Documentation**](./docs/PIPELINE.md) - Numaflow vertex details and scaling.

---

## 🏗️ Architecture at a Glance

The system is designed to run on Kubernetes (Minikube for local dev).

1. **Ingestion**: Sensors push data to **Kafka**.
2. **Processing**: **Numaflow** pipeline consumes from Kafka and runs the **ML Runtime UDF**.
3. **Inference**: The Python-based UDF calculates features and predicts RUL.
4. **Storage**: Predictions are sent back to Kafka, processed by **Logstash**, and stored in **Elasticsearch**.
5. **Visualization**: **Kibana** provides real-time health dashboards.

---

## 🛠️ Getting Started (Local Setup)

If you already have Minikube and Docker installed, follow these steps to spin up the stack.

### 1. Clone the repository

```bash
git clone https://github.com/mr-mandeeprana/belt-ml-runtime.git
cd belt-ml-runtime
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the Full Stack

Execute the automated startup script:

```powershell
.\start-all.ps1
```

*This script will:*

- Start Minikube.
- Install Numaflow.
- Build the ML Runtime Docker image.
- Deploy Kafka, Elasticsearch, Kibana, and the Numaflow Pipeline.
- Establish port-forwards and open Kibana in your browser.

---

## 📂 Project Structure

- `app/`: Core Python application logic (Feature engineering, Inference).
- `deploy/`: Kubernetes manifests (Kafka, ES, Numaflow Pipeline).
- `docs/`: In-depth documentation for installation, architecture, and pipeline.
- `model/`: Pre-trained scikit-learn models and configuration.
- `scripts/`: Operational scripts (e.g., `delta_catchup.py`).
- `belt-stream-pipeline.yaml`: Numaflow pipeline specification.

---

## 🔧 Operational Commands

### View Logs

```powershell
# View ML Runtime logs
kubectl logs -l numaflow.numaproj.io/vertex-name=ml-runtime -c main -f
```

### Check Stack Status

```powershell
kubectl get pods -A
```

### Access Dashboards

- **Kibana**: [http://localhost:5601](http://localhost:5601)
- **Numaflow UX**: [https://localhost:8443](https://localhost:8443) (default credentials: `admin/admin`)

---

## 📜 License

Internal / Proprietary
