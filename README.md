# Belt ML Runtime

Real-time Remaining Useful Life (RUL) prediction runtime for conveyor belts. This system leverages Kafka for data ingestion, Numaflow for stream processing, and Elasticsearch for storage and observability.

## Architecture

- **Kafka Source**: Ingests sensor data from edge devices.
- **Numaflow Pipeline**: Orchestrates the ML inference workload.
- **ML Runtime (pynumaflow)**: A Python-based User Defined Function (UDF) that performs feature engineering and RUL prediction using scikit-learn models.
- **Elasticsearch**: Persists predictions and metadata for downstream visualization and analysis.

## Project Structure

- `app/`: Core application logic and Numaflow UDF entry point.
- `deploy/`: Infrastructure as Code (IaC) and deployment configurations (Logstash, etc.).
- `model/`: Pre-trained ML models and configuration files.
- `scripts/`: Operational scripts for data catchup and troubleshooting.
- `belt-stream-pipeline.yaml`: Numaflow pipeline specification.
- `start-all.ps1`: Convenience script to spin up the local stack.
- `Dockerfile`: Container definition for the ML runtime UDF.

## Getting Started

### Prerequisites

- Python 3.9+
- Docker & Kubernetes (with Numaflow installed)
- Kafka Cluster
- Elasticsearch Cluster

### Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/[username]/belt-ml-runtime.git
   cd belt-ml-runtime
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

### Running Locally

Execute the startup script to initialize the stack:

```powershell
.\start-all.ps1
```

## Configuration

The model behavior and runtime parameters can be tuned via configuration files in the `model/` directory, including thresholds and feature mappings.

## License

Internal / Proprietary
