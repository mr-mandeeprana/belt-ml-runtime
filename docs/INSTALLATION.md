# Installation Guide: Belt ML Runtime

This guide provides step-by-step instructions to set up the Belt ML Runtime environment on a new Windows system using Minikube.

## Prerequisites

Before starting, ensure your system meets these requirements:

- **OS**: Windows 10/11 (Pro, Enterprise, or Education recommended for Hyper-V, but Home works with WSL2).
- **Virtualization**: Enabled in BIOS/UEFI.
- **CPU**: 4+ Cores recommended.
- **RAM**: 8GB+ (The stack requires ~6GB dedicated to Minikube).

## 1. Install Required Tools

The easiest way to install these tools is via [Chocolatey](https://chocolatey.org/) or [Scoop](https://scoop.sh/).

### Method A: Chocolatey (Recommended)

Open PowerShell as **Administrator** and run:

```powershell
# Install Chocolatey (if not already installed)
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install Minikube, Kubectl, and Helm
choco install minikube kubernetes-cli helm -y
```

### Method B: Manual Download

- **Minikube**: Download `shared-windows-amd64.exe` from [Minikube Releases](https://github.com/kubernetes/minikube/releases).
- **Kubectl**: Download from [Kubernetes Docs](https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/).

## 2. Install Docker Desktop (Driver)

Minikube requires a hypervisor or container runtime. **Docker Desktop** with the **WSL2 backend** is highly recommended.

1. Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop/).
2. During installation, select "Use WSL 2 instead of Hyper-V".
3. Restart your computer if prompted.
4. Ensure Docker is running before proceeding.

## 3. Initialize Minikube

Start Minikube with sufficient resources for the ML stack:

```powershell
minikube start --memory=6144 --cpus=3 --driver=docker
```

## 4. Enable Required Addons

```powershell
minikube addons enable dashboard
minikube addons enable metrics-server
```

## 5. Verify Installation

```powershell
kubectl get nodes
# Should show one node (minikube) with status 'Ready'
```

---

Next Step: [Project Setup & Running Locally](../README.md#running-locally)
