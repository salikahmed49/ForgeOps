# The Complete Cloud, DevOps & Site Reliability Engineering Master Handbook

> **Author**: Staff Platform & DevOps Architect  
> **Platform Reference**: ForgeOps Enterprise Platform  
> **Scope**: Microsoft Azure, Docker, Kubernetes, Helm, Terraform, Prometheus, and Grafana  

---

# Table of Contents
1. [Chapter 1: Microsoft Azure & Enterprise Cloud Architecture](#chapter-1-microsoft-azure--enterprise-cloud-architecture)
2. [Chapter 2: Docker & Containerization Deep Dive](#chapter-2-docker--containerization-deep-dive)
3. [Chapter 3: Kubernetes (K8s) & Helm Orchestration Mastery](#chapter-3-kubernetes-k8s--helm-orchestration-mastery)
4. [Chapter 4: Terraform & Infrastructure as Code (IaC) Mastery](#chapter-4-terraform--infrastructure-as-code-iac-mastery)
5. [Chapter 5: Prometheus & Grafana Observability (SRE Mastery)](#chapter-5-prometheus--grafana-observability-sre-mastery)
6. [Chapter 6: Commonly Used CLI Cheat Sheet (Docker, Kubectl, Helm, Terraform, Azure)](#chapter-6-commonly-used-cli-cheat-sheet)

---

# Chapter 1: Microsoft Azure & Enterprise Cloud Architecture

## 1.1 The Fundamentals of Cloud Computing
Cloud computing is the on-demand availability of computer system resources—especially data storage (cloud storage) and computing power (virtual machines, containers)—without direct active physical management by the user.

### Service Models:
* **IaaS (Infrastructure as a Service)**: Provides virtualized computing resources over the internet. You manage the Operating System, middleware, runtime, data, and applications. Azure manages virtualization, servers, storage, and networking.
  - *Azure Examples*: Azure Virtual Machines, Virtual Machine Scale Sets (VMSS), Azure Virtual Network (VNet).
* **PaaS (Platform as a Service)**: Provides a hardware and software tools framework. The cloud provider manages the operating system, patching, runtime, and hardware. You only manage application code and data.
  - *Azure Examples*: Azure App Service, Azure Container Apps, Azure SQL Database.
* **SaaS (Software as a Service)**: Complete end-user applications managed entirely by the vendor.
  - *Azure Examples*: Microsoft 365, Dynamics 365.

---

## 1.2 Azure Resource Hierarchy & Governance
Azure organizes every asset in a strict 4-level management hierarchy:

```
[1] Microsoft Entra ID Tenant (Identity Boundary)
      └── [2] Management Groups (Governance & Azure Policy Boundary)
            └── [3] Azure Subscription (Billing & Quota Boundary)
                  └── [4] Resource Groups (Lifecycle & Containment Boundary)
                        ├── Virtual Network (VNet)
                        ├── Azure Kubernetes Service (AKS)
                        ├── Azure Container Registry (ACR)
                        └── Azure Key Vault
```

1. **Entra ID Tenant (formerly Azure AD)**: Represents an organization. Contains users, groups, application registrations, and enterprise service principals.
2. **Management Groups**: Containers to manage access, policy, and compliance across multiple subscriptions.
3. **Subscription**: An agreement with Microsoft to use cloud services. Invoices and credit limits (such as free trial credits) exist at this level.
4. **Resource Group**: A logical container into which Azure resources are deployed and managed. **Crucial Rule**: Deleting a Resource Group automatically cascades and deletes every resource within it.

---

## 1.3 Azure Global Infrastructure
* **Regions**: Geographic areas containing at least one, but often multiple, physical data centers connected through a dedicated low-latency network (e.g., `East US`, `West Europe`, `Southeast Asia`).
* **Availability Zones (AZs)**: Unique, physically separate data centers within an Azure Region. Each zone has independent power, cooling, and networking. Running workloads across 3 AZs provides a **99.99% uptime SLA** against physical data center fires or electrical failures.
* **Paired Regions**: Each Azure region is paired with another region in the same geography (e.g., `East US` paired with `West US`) for disaster recovery and sequential platform updates.

---

## 1.4 Azure Networking Deep Dive
* **Virtual Network (VNet)**: A private, isolated network in Azure with customizable IP address blocks (e.g., `10.0.0.0/16`).
* **Subnets**: Subdivisions of a VNet (e.g., `10.0.1.0/24`) isolating tiers (e.g., frontend subnets, AKS node subnets, private database subnets).
* **Network Security Groups (NSGs)**: Stateful firewall filters controlling inbound and outbound traffic. Uses 5-tuple evaluation:
  1. Source IP/CIDR
  2. Source Port
  3. Destination IP/CIDR
  4. Destination Port
  5. Protocol (TCP/UDP/ICMP)
* **VNet Peering**: Directly connects two Azure VNets using Microsoft's private optical backbone with zero internet exposure and ultra-low latency.
* **Azure Bastion**: A fully managed PaaS service that provides secure RDP/SSH access to VMs directly through the Azure Portal via TLS (port 443), eliminating the need for public IP addresses on servers.

---

## 1.5 Azure Container & Identity Services
* **Azure Container Registry (ACR)**: Private OCI-compliant registry.
  - *Hardening Best Practice*: Set `admin_enabled = false`. Authenticate nodes via Managed Identities rather than permanent root passwords.
* **Azure Kubernetes Service (AKS)**: Managed Kubernetes. Microsoft manages the control plane (`kube-apiserver`, `etcd`) for free; you only pay for worker node VMs.
  - *Networking Modes*: **Kubenet** (overlay virtual network, saves IP space) vs **Azure CNI** (every pod gets a direct, routable Azure VNet IP).
* **Managed Identities**:
  - **System-Assigned**: Tied directly to an Azure resource's lifecycle (e.g., AKS kubelet). If the resource is destroyed, the identity is automatically deleted.
  - **User-Assigned**: Independent identity resource that can be assigned to multiple VMs or clusters.
  - *How it works*: Azure injects tokens via a local Instance Metadata Service (IMDS) at `http://169.254.169.254`. No secret credentials ever exist in config files.

---

# Chapter 2: Docker & Containerization Deep Dive

## 2.1 How Containers Work Under the Hood
Containers are **NOT** virtual machines. A virtual machine virtualizes the physical hardware and runs a full guest operating system with its own kernel. A container is simply an **isolated Linux process** running directly on the host kernel.

```
+---------------------------------------------------------------+
|                      Application Process                      |
+---------------------------------------------------------------+
| Linux Namespaces (Visibility) | cgroups (Resource Constraints)|
| - PID: Process ID Isolation   | - CPU Shares & Quotas         |
| - NET: Network Interfaces/IPs | - Memory Limits (OOM Killer)  |
| - MNT: Filesystem Mount Points| - Block I/O Throughput        |
| - IPC: Inter-Process Comm     |                               |
+---------------------------------------------------------------+
|            Shared Host Linux Kernel (kernel.org)              |
+---------------------------------------------------------------+
```

### The Three Linux Pillars:
1. **Linux Namespaces (What a process can SEE)**:
   - `PID Namespace`: Process isolation (inside the container, your app is PID 1).
   - `NET Namespace`: Network virtualization (each container gets its own `eth0` and IP).
   - `MNT Namespace`: Filesystem isolation (restricts process to container rootfs).
   - `IPC Namespace`: Inter-Process Communication isolation.
   - `UTS Namespace`: Hostname isolation.
   - `USER Namespace`: Maps in-container root (UID 0) to an unprivileged host UID.
2. **Control Groups (cgroups) (What a process can USE)**:
   - Restricts CPU quotas, memory limits, and disk I/O. If a container exceeds its memory limit, the Linux kernel invokes the `OOM Killer` (Out Of Memory) to terminate it.
3. **Union Filesystem (OverlayFS / Overlay2)**:
   - Stacks multiple read-only image layers together with a thin read-write container layer on top using copy-on-write (CoW).

---

## 2.2 Dockerfile Mastery & Best Practices

```dockerfile
# 1. Base Image: Use explicit, minimal Debian/Alpine tags
FROM python:3.12-slim

# 2. Environment Variables: Prevent Python from writing .pyc or buffering logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

WORKDIR /app

# 3. Layer Caching: Copy dependencies FIRST, before application code
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 4. Copy Code
COPY app ./app
COPY tests ./tests

# 5. Security Hardening: Never run as root (UID 0)
RUN useradd --create-home --uid 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# 6. Entrypoint: Always use JSON exec form (handles POSIX SIGTERM correctly)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Critical Rules:
* **JSON Exec Form (`["app"]`) vs Shell Form (`app`)**:
  - `CMD ["node", "server.js"]`: Runs as PID 1. Receives `SIGTERM` signals directly from Docker/Kubernetes for graceful shutdown.
  - `CMD node server.js`: Spawns `/bin/sh -c node server.js`. Signals are swallowed by the shell, causing Kubernetes to wait 30s before forceful `SIGKILL`.
* **Multi-Stage Builds**: Compile binaries in a heavy `builder` stage, then copy only the compiled binary into a minimal `scratch` or `distroless` stage, dropping image sizes from 1GB+ down to <50MB.

---

# Chapter 3: Kubernetes (K8s) & Helm Orchestration Mastery

## 3.1 The Kubernetes Architecture

```
                    KUBERNETES CONTROL PLANE
+---------------------------------------------------------------+
|  +----------------+     +------------------+     +---------+  |
|  | kube-apiserver |<--->|      etcd        |<--->| kube-   |  |
|  | (REST Gateway) |     | (Consensus Store)|     | scheduler| |
|  +--------^-------+     +------------------+     +---------+  |
|           |                                                   |
|  +--------v-------------------+                               |
|  |  kube-controller-manager   |                               |
|  +----------------------------+                               |
+---------------------------------------------------------------+
                         | Network
                         v
                    WORKER NODES
+---------------------------------------------------------------+
|  +--------------------+             +----------------------+  |
|  | kubelet (Node Mgr) |             | kube-proxy (Network) |  |
|  +---------^----------+             +----------------------+  |
|            | CRI (Container Runtime Interface)                |
|  +---------v----------+             +----------------------+  |
|  | containerd runtime |             | Pod: [App] [Sidecar] |  |
|  +--------------------+             +----------------------+  |
+---------------------------------------------------------------+
```

### Control Plane Components:
1. **`kube-apiserver`**: The front door of the cluster. All internal and external requests (`kubectl`) authenticate and validate through this REST API.
2. **`etcd`**: A highly available, distributed, key-value database implementing the Raft consensus algorithm. Stores the entire desired and actual cluster state.
3. **`kube-scheduler`**: Watches for newly created unscheduled Pods. Evaluates node resource availability, affinity, and taints/tolerations to assign the pod to the best worker node.
4. **`kube-controller-manager`**: Runs continuous reconciliation loops. Compares current state with desired state (e.g., if desired replicas = 3 and only 2 exist, it requests a new pod creation).

### Worker Node Components:
1. **`kubelet`**: The node agent. Watches the API server for PodSpecs assigned to its node and instructs the container runtime (`containerd`) to start or stop containers.
2. **`kube-proxy`**: Manages network routing rules on worker nodes (via Linux `iptables` or IPVS), load-balancing traffic across pods backing a `Service`.
3. **Container Runtime (`containerd`)**: Pulls images, manages storage layers, and starts containers using Linux namespaces and cgroups.

---

## 3.2 Core Kubernetes Primitives

### 1. Pods vs. Deployments vs. ReplicaSets
* **Pod**: The atomic unit of deployment. Contains one or more tightly coupled containers sharing localhost (`127.0.0.1`), storage volumes, and network namespace.
* **ReplicaSet**: Ensures a specified number of identical pod replicas are running at all times.
* **Deployment**: Higher-level abstraction over ReplicaSets. Manages declarative zero-downtime rolling updates and rollbacks.
  - `maxSurge: 1`: Allows 1 extra pod above desired count during updates.
  - `maxUnavailable: 0`: Guarantees 0 pods can be taken down until new pods pass their readiness checks.

### 2. Services: Networking & Load Balancing
Pods are ephemeral—their IP addresses change when recreated. A **Service** provides a stable virtual IP and DNS name:
* **`ClusterIP` (Default)**: Exposes service internally within the cluster network only.
* **`NodePort`**: Exposes service on a static high port (`30000-32767`) on every physical node IP.
* **`LoadBalancer`**: Integrates with cloud providers (Azure Load Balancer) to provision an external public IP routing into the cluster.
* **`Headless Service` (`clusterIP: None`)**: Returns direct Pod IPs via DNS rather than a virtual IP (used for stateful clusters like Cassandra, Kafka).

### 3. Ingress & TLS Termination
An **Ingress Controller** (e.g., NGINX Ingress) operates as an Application Gateway (Layer 7 HTTP reverse proxy). Routes traffic to hundreds of backend Services based on Host header (`api.domain.com`) or URI Path (`/auth`, `/orders`), while terminating SSL/TLS certificates via `cert-manager` and Let's Encrypt.

### 4. Pod Health Checks (Probes)
* **Liveness Probe**: Detects deadlocks or unrecoverable application crashes. If it fails, Kubernetes restarts the container.
* **Readiness Probe**: Determines if the application is ready to accept user traffic (e.g., database connections established). If it fails, Kubernetes removes the pod from the Service endpoint pool.
* **Startup Probe**: Disables liveness checks during slow legacy application initialization to prevent premature restart loops.

---

## 3.3 Helm 3: Package Management for Kubernetes
Helm acts as both package manager and Go-templating engine for Kubernetes manifests:

```text
charts/forgeops-api/
├── Chart.yaml         # Package metadata, version, appVersion
├── values.yaml        # Default configuration variables
├── values-dev.yaml    # Dev environment overrides
├── values-prod.yaml   # Production environment overrides
└── templates/         # Templated Kubernetes manifests
    ├── _helpers.tpl   # Named Go template definitions
    ├── deployment.yaml
    ├── service.yaml
    └── hpa.yaml
```

* **Templating Syntax**: `{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}`
* **Atomic Upgrades**: `helm upgrade --install forgeops-api ./charts/forgeops-api --atomic --timeout 5m`  
  *If any pod fails its readiness check within 5 minutes, Helm automatically rolls back to the previous release revision.*

---

# Chapter 4: Terraform & Infrastructure as Code (IaC) Mastery

## 4.1 Principles of Infrastructure as Code
* **Declarative**: Define *what* the infrastructure should be, not *how* to build it.
* **Idempotency**: Running `terraform apply` 100 times produces the exact same end state as running it once.
* **Immutable Infrastructure**: Instead of modifying servers in place, replace them with newly versioned resources.

---

## 4.2 State Management & Remote State Locking
* **`terraform.tfstate`**: A JSON ledger mapping declared resources to actual cloud IDs (`/subscriptions/.../resourceGroups/...`).
* **Remote Backend with Locking (Azure Blob Storage)**:
  ```hcl
  terraform {
    backend "azurerm" {
      resource_group_name  = "rg-forgeops-tfstate"
      storage_account_name = "stforgeopstfstate"
      container_name       = "tfstate"
      key                  = "forgeops.dev.terraform.tfstate"
    }
  }
  ```
  *When a developer or CI runs `terraform apply`, an exclusive Azure Blob Storage Lease is acquired. Concurrent runs are rejected, preventing state corruption.*

---

## 4.3 Modular Architecture
```
terraform/
├── backend.tf
├── main.tf
├── variables.tf
├── outputs.tf
└── modules/
    ├── networking/ (VNet, Subnet)
    ├── acr/        (Azure Container Registry)
    └── aks/        (Managed Cluster, AcrPull RBAC)
```

* **Module Composition**: Root [`main.tf`](file:///d:/devops-automation-platform/terraform/main.tf) passes inputs into child modules and wires outputs together (e.g., passing `module.networking.aks_subnet_id` into `module.aks`).

---

# Chapter 5: Prometheus & Grafana Observability (SRE Mastery)

## 5.1 Google SRE's 4 Golden Signals
1. **Latency**: The time it takes to service a request. Tracked using p50 (median), p90, and p99 percentiles rather than misleading averages.
2. **Traffic**: The demand placed on your system (e.g., HTTP Requests Per Second).
3. **Errors**: The rate of requests that fail (e.g., HTTP 5xx responses).
4. **Saturation**: How full your computing resources are (e.g., Memory/CPU utilization, disk space).

---

## 5.2 Prometheus Architecture & Metric Types
Prometheus uses a **Pull Model**, scraping HTTP endpoints (`/metrics`) exposing metrics in open text format every 5–15 seconds.

### The 4 Metric Types:
1. **Counter**: Cumulative metric that only increases (or resets to zero on restart).
   - *Example*: `api_requests_total{method="GET", status="200"}`
2. **Gauge**: Value that can arbitrarily go up or down.
   - *Example*: `active_users_current`, `memory_bytes_used`
3. **Histogram**: Samples observations into configurable buckets and counts total observations.
   - *Example*: `api_request_duration_seconds_bucket{le="0.1"}`
4. **Summary**: Calculates configurable quantiles client-side directly over sliding time windows.

---

## 5.3 Essential PromQL Formulas

1. **Calculate Requests Per Second (RPS)**:
   ```promql
   sum(rate(api_requests_total[1m]))
   ```
2. **Calculate HTTP 5xx Error Rate Percentage**:
   ```promql
   (sum(rate(api_requests_total{status=~"5.."}[1m])) / sum(rate(api_requests_total[1m]))) * 100
   ```
3. **Calculate 95th Percentile Response Time (Latency)**:
   ```promql
   histogram_quantile(0.95, sum by (le) (rate(api_request_duration_seconds_bucket[1m])))
   ```
4. **Detect Down Instances**:
   ```promql
   up{job="forgeops-api"} == 0
   ```

---

# Chapter 6: Commonly Used CLI Cheat Sheet

## Docker CLI
```bash
# Container lifecycle
docker run -d --name api -p 8000:8000 --restart unless-stopped forgeops-api:latest
docker ps -a                                # List all running and stopped containers
docker stop <container_id>                  # Send SIGTERM, then SIGKILL after 10s
docker kill <container_id>                  # Send immediate SIGKILL (crash simulation)
docker rm -f <container_id>                 # Force remove container

# Inspection & debugging
docker logs -f --tail 100 api               # Follow live log stream
docker exec -it api /bin/sh                 # Open interactive terminal inside container
docker inspect api                          # Detailed JSON metadata (IPs, mounts, env)
docker stats                                # Live CPU/RAM stream for all containers

# Images & build
docker build -t forgeops-api:1.0.0 .        # Build container image from Dockerfile
docker images                               # List local images and sizes
docker rmi <image_id>                       # Remove image from local cache
docker system prune -af --volumes           # Clean up all dangling containers, images, and volumes
```

---

## Kubernetes (`kubectl`) CLI
```bash
# Cluster & context
kubectl cluster-info                        # Display API server endpoint
kubectl get nodes -o wide                   # List physical/virtual worker nodes
kubectl config get-contexts                 # List available kubeconfig clusters
kubectl config use-context <name>           # Switch active cluster context

# Workloads
kubectl get pods -n forgeops                # List pods in namespace
kubectl get pods -A                         # List pods across ALL namespaces
kubectl describe pod <pod_name> -n forgeops # View detailed events and failure reasons
kubectl logs -f <pod_name> -n forgeops      # Stream live pod logs
kubectl delete pod <pod_name> -n forgeops   # Terminate pod (tests self-healing)

# Deployments & scaling
kubectl apply -k k8s/                       # Apply kustomize resources
kubectl rollout status deployment/api -n ns # Monitor zero-downtime rollout
kubectl rollout undo deployment/api -n ns   # Rollback to previous revision
kubectl scale deployment/api --replicas=5   # Manually scale pod replicas

# Port-forwarding (local debug)
kubectl port-forward svc/forgeops-api 8080:80 -n forgeops
```

---

## Helm 3 CLI
```bash
helm lint charts/forgeops-api               # Validate chart syntax and best practices
helm template charts/forgeops-api           # Render templates to stdout without applying
helm install forgeops-api ./charts/forgeops-api -n forgeops --create-namespace --dry-run
helm upgrade --install forgeops-api ./charts/forgeops-api -n forgeops --atomic --timeout 5m
helm list -n forgeops                       # List active releases
helm history forgeops-api -n forgeops       # View release revision history
helm rollback forgeops-api 2 -n forgeops    # Instant rollback to release revision 2
```

---

## Terraform CLI
```bash
terraform -chdir=terraform init             # Initialize backend & download provider plugins
terraform -chdir=terraform fmt              # Auto-format HCL code to HashiCorp standard
terraform -chdir=terraform validate         # Check code syntax and internal consistency
terraform -chdir=terraform plan             # Calculate graph diff and preview actions
terraform -chdir=terraform apply            # Provision live cloud infrastructure
terraform -chdir=terraform destroy          # Tear down all managed cloud resources
terraform -chdir=terraform state list       # List all resources tracked in state
terraform -chdir=terraform output           # Display declared output values
```

---

## Azure CLI (`az`)
```bash
az login                                    # Interactive browser login to Microsoft Azure
az account show                             # View active subscription and tenant details
az account set --subscription <sub_id>      # Switch active billing subscription
az group list -o table                      # List all Resource Groups
az aks list -o table                        # List all AKS Kubernetes clusters
az aks get-credentials -g rg-name -n aks-name --overwrite-existing # Sync kubeconfig
az acr login --name acrname                 # Authenticate local Docker daemon with ACR
az resource list -g rg-name -o table        # List all resources inside a Resource Group
```
