# HashTensor Kaspa Validator

A plug-and-play validator for the Bittensor network that tracks Kaspa GPU miners and helps secure the network by providing real-time ratings based on mining activity.

## What is this?
This service connects your Bittensor hotkey to a Kaspa mining worker, monitors its performance, and submits ratings to the Bittensor network. It is designed to be easy to run and requires minimal setup.

## Why run this validator?
- Help secure the Bittensor network
- Earn potential rewards for validating miners
- Simple setup with Docker

## System Overview

Below is a high-level diagram showing how Kaspa miners, the validator, and Bittensor interact:

```mermaid
flowchart TD

%% ==== Miner Identity ====
subgraph "Miner"
    GPU["GPU / ASIC"]
    Hotkey["Bittensor Hotkey"]
end

%% ==== Kaspa Block ====
subgraph "Kaspa Block"
    Kaspad["Kaspad Node"]
    Bridge["Kaspa Stratum Bridge"]
    Prometheus["Prometheus"]
    Grafana["Grafana Dashboard"]

    GPU -->|"Stratum connection"| Bridge
    Bridge -->|"New block templates / submit shares"| Kaspad
    Bridge -->|"Metrics (per worker)"| Prometheus
    Prometheus --> Grafana
    Bridge -->|"All KAS mined →"| Owner["Pool Owner Kaspa Wallet"]
end

%% ==== Bittensor Block ====
subgraph "Bittensor Block"
    Validator["HashTensorValidator"]
    Mapping["Hotkey <-> Worker Mapping DB"]
    ValidatorAPI["Validator API / Mapping Registrar"]
    Yuma["Yuma Consensus"]
    SubnetBoost["Subnet Emission Boost"]

    Validator -->|"Fetch metrics"| Prometheus
    Validator -->|"Lookup mapping"| Mapping
    Validator -->|"Send ratings"| Yuma
    ValidatorAPI --> Mapping
    Hotkey -->|"Register hotkey + worker + signature"| ValidatorAPI
    Yuma -->|"Alpha reward to hotkey"| Hotkey
    SubnetBoost -->|"Increases TAO/day"| Yuma
end

%% ==== Ownership & Emission Loop ====
Owner -->|Sends KAS| CEX["CEX / OTC Exchange"]
CEX -->|"Convert KAS → TAO"| OwnerTAO["Owner's TAO Wallet"]
OwnerTAO -->|"Stake / Buyback Alpha"| SubnetBoost
```

*Diagram: Flow of mining, metrics, mapping, and rewards between Kaspa, Bittensor, and the validator.*

## Quick Start (Recommended: Docker Compose)

1. **Clone this repository**
   ```sh
   git clone <this-repo-url>
   cd HashTensor
   ```

2. **Configure your environment**
   - Copy `.env.example` to `.env` and edit values as needed (wallet, hotkey, etc.), or set environment variables directly.
   - By default, the validator uses a local SQLite database and connects to the public Kaspa pool and Prometheus endpoint.

3. **Start the validator**
   ```sh
   docker-compose up -d
   ```
   This will start both the validator and an auto-updating service (watchtower).

4. **Check if it's running**
   Visit [http://localhost:8000/health](http://localhost:8000/health) in your browser. You should see:
   ```json
   {"status": "OK"}
   ```

## Registering Your Worker
To link your Bittensor hotkey with a Kaspa worker:
1. Use the `/register` endpoint (see API docs or use a tool like `curl` or Postman).
2. Provide your hotkey, worker name, and signature as required.

## Viewing Metrics and Ratings
- **Metrics:** [http://localhost:8000/metrics](http://localhost:8000/metrics)
- **Ratings:** [http://localhost:8000/ratings](http://localhost:8000/ratings)

## Configuration
Most settings can be changed via environment variables in `docker-compose.yml`:
- `WALLET_NAME`, `WALLET_HOTKEY`, `WALLET_PATH`: Your Bittensor wallet info
- `KASPA_POOL_OWNER_WALLET`: Kaspa pool wallet address
- `PROMETHEUS_ENDPOINT`: Where to fetch miner stats
- `SUBTENSOR_NETWORK`: Bittensor network (e.g., `finney`)

## Requirements
- Docker and Docker Compose
- (Advanced) Python 3.12+ if running without Docker
