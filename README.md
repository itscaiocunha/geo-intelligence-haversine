# Tactical Geo-Intelligence Haversine API

High-precision geospatial distance and perimeter intelligence service built with FastAPI and a clean, layered architecture.  
It provides secure API-key access, unitary and batch geospatial analysis, and audit-oriented operational logging.

## Table of Contents

- [Overview](#overview)
- [Core Capabilities](#core-capabilities)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [Run with Docker](#run-with-docker)
- [Run Locally](#run-locally)
- [API Reference](#api-reference)
- [CSV Batch Format](#csv-batch-format)
- [Audit and Observability](#audit-and-observability)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Known Gaps and Next Improvements](#known-gaps-and-next-improvements)
- [License](#license)

## Overview

This project implements a tactical geospatial engine centered on the Haversine formula.

Main operational goals:
- Compute distances between two coordinates with validation safeguards.
- Detect radius/perimeter violations for rapid proximity alerts.
- Process multiple targets from CSV in a single mission-oriented request.
- Keep auditable operation traces for command-level inspection.

The service is designed as an API-first backend suitable for intelligence, logistics, monitoring, and geofencing workflows.

## Core Capabilities

- **Precise geospatial computation** using a domain-level `HaversineEngine`.
- **Coordinate integrity checks** (`latitude` and `longitude` bounds) via immutable `Coordinate` entities.
- **Single target analysis** via `POST /calculate`.
- **Batch mission analysis** via `POST /calculate/batch` with CSV upload.
- **Role-aware key management** via `POST /admin/generate-key`.
- **Audit reporting** based on operation logs via `GET /admin/stats`.

## Architecture

The codebase follows a clear separation of concerns:

- **Domain** (`src/domain`): pure business rules and geospatial math.
- **Application** (`src/application`): use-case orchestration and report assembly.
- **Infrastructure** (`src/infrastructure`): HTTP API, environment loading, authentication, and logging setup.

This structure keeps critical geospatial logic independent from transport and framework details.

## Tech Stack

- Python 3.11
- FastAPI
- Pydantic
- Uvicorn
- python-dotenv
- Pytest
- Docker / Docker Compose

## Project Structure

```text
.
├─ src/
│  ├─ application/
│  │  └─ use_cases.py
│  ├─ domain/
│  │  └─ entities.py
│  └─ infrastructure/
│     ├─ api.py
│     └─ logger_config.py
├─ tests/
│  ├─ test_api.py
│  └─ test_engine.py
├─ targets.csv
├─ Dockerfile
├─ docker-compose.yml
├─ pytest.ini
└─ README.md
```

## Quick Start

1. Create an environment file with a command-level key.
2. Start the API (Docker or local).
3. Use the command key in `X-API-KEY`.
4. Optionally generate operator keys for delegated access.

## Configuration

Environment variables:

- `API_KEY_COMMAND` (required): bootstrap command-level key loaded at startup.

Example `.env`:

```env
API_KEY_COMMAND=geo_command_master_change_me
```

Without `API_KEY_COMMAND`, privileged operations and normal authenticated flows will fail.

## Run with Docker

```bash
docker compose up --build
```

Expected API base URL:

```text
http://localhost:8000
```

Open API docs:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Run Locally

### 1) Create and activate a virtual environment

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

### 2) Install dependencies

This repository expects typical runtime dependencies:
- `fastapi`
- `uvicorn`
- `pydantic`
- `python-dotenv`
- `python-multipart` (required for file uploads)
- `pytest` (for testing)

Install manually (until a dependency manifest is added):

```bash
pip install fastapi uvicorn pydantic python-dotenv python-multipart pytest
```

### 3) Start the server

```bash
uvicorn src.infrastructure.api:app --host 0.0.0.0 --port 8000 --reload
```

## API Reference

All protected routes require:

- Header: `X-API-KEY: <your_key>`

### 1) Generate API key (COMMAND only)

- **Method:** `POST`
- **Path:** `/admin/generate-key`
- **Purpose:** creates a new role-scoped key.

Request body:

```json
{
  "role": "OPERATOR",
  "owner_name": "Agent-07",
  "expires_in_days": 30
}
```

Example:

```bash
curl -X POST "http://localhost:8000/admin/generate-key" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: geo_command_master_change_me" \
  -d "{\"role\":\"OPERATOR\",\"owner_name\":\"Agent-07\",\"expires_in_days\":30}"
```

### 2) Get audit statistics (COMMAND only)

- **Method:** `GET`
- **Path:** `/admin/stats`

Example:

```bash
curl -X GET "http://localhost:8000/admin/stats" \
  -H "X-API-KEY: geo_command_master_change_me"
```

### 3) Calculate distance and perimeter status

- **Method:** `POST`
- **Path:** `/calculate`

Request body:

```json
{
  "origin": { "lat": -15.7942, "lon": -47.8822 },
  "target": { "lat": -15.8010, "lon": -47.8920 },
  "radius": 5.0
}
```

Example:

```bash
curl -X POST "http://localhost:8000/calculate" \
  -H "Content-Type: application/json" \
  -H "X-API-KEY: <operator_or_command_key>" \
  -d "{\"origin\":{\"lat\":-15.7942,\"lon\":-47.8822},\"target\":{\"lat\":-15.8010,\"lon\":-47.8920},\"radius\":5.0}"
```

### 4) Batch calculation from CSV

- **Method:** `POST`
- **Path:** `/calculate/batch`
- **Content-Type:** `multipart/form-data`

Form fields:
- `lat` (float): origin latitude
- `lon` (float): origin longitude
- `radius` (float): alert radius in kilometers
- `file` (csv): target list

Example:

```bash
curl -X POST "http://localhost:8000/calculate/batch" \
  -H "X-API-KEY: <operator_or_command_key>" \
  -F "lat=-15.7942" \
  -F "lon=-47.8822" \
  -F "radius=5.0" \
  -F "file=@targets.csv"
```

## CSV Batch Format

Required headers:

```csv
name,lat,lon
Target_Alpha,-23.5505,-46.6333
Target_Bravo,-23.5600,-46.6400
```

Notes:
- Invalid rows are skipped.
- `name` is optional in runtime handling; fallback label is used if absent.
- Distances are returned in kilometers and rounded to 2 decimals.

## Audit and Observability

The service logs tactical events to:

- `data/operation.log`

Logged operation types include:
- `CALC_UNITARY`
- `BATCH_OPERATION`
- `KEY_GEN`

`/admin/stats` parses this log and builds:
- global operation counters
- violation totals
- per-agent activity details

## Testing

Run all tests:

```bash
pytest
```

Test layout:
- `tests/test_engine.py`: geospatial domain and invariants.
- `tests/test_api.py`: authentication and endpoint behavior.

## Troubleshooting

- **403 Missing/Invalid Credentials**  
  Ensure `X-API-KEY` is present and valid.

- **Command endpoints denied**  
  Use the command key (`API_KEY_COMMAND`) for `/admin/*`.

- **File upload fails on batch endpoint**  
  Ensure `python-multipart` is installed.

- **No audit report data**  
  `data/operation.log` is created after first operations; run some requests first.

- **Docker build fails on missing dependencies file**  
  The current `Dockerfile` references `requirements.txt`, which is not currently present in this repository.

## Known Gaps and Next Improvements

- Add a versioned `requirements.txt` or `pyproject.toml` for deterministic installs.
- Provide `.env.example` for first-run onboarding.
- Align API tests with current response contracts (`tests/test_api.py` vs current endpoint payloads).
- Replace in-memory API key storage with persistent secure storage for production.
- Add rate limiting and key revocation endpoints.
- Add CI pipeline (lint, test, image build, security scan).

## License

This project is distributed under the terms defined in the `LICENSE` file.
