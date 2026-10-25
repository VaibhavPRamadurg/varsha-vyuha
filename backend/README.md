# FloodShift AI backend

This is a deterministic FastAPI simulation backend for the bundled synthetic Mumbai fixture. It is not a flood forecast, emergency warning, or navigation service.

## Run locally

From the repository root, create and activate a virtual environment, then install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r backend/requirements.txt
PYTHONPATH=backend uvicorn app.main:app --reload
```

The API is then available at `http://127.0.0.1:8000`; interactive documentation is at `/docs`.

## Test

```bash
PYTHONPATH=backend pytest backend/tests -q
```

The tests cover endpoint contracts, synthetic provenance, input validation, dataset checksum exposure, and the invariant that a higher rainfall multiplier cannot lower a cell's score when blockage and cell selection are unchanged.

## Endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Service, model version, and synthetic provenance. |
| `GET /layers` | Synthetic grid layer catalogue. |
| `GET /areas` | Compact Mumbai demo area and valid cell IDs. |
| `GET /metadata/datasets` | Verified dataset manifests. |
| `POST /scenario/evaluate` | Deterministic scenario risk for selected grid cells. |

Example request:

```bash
curl -X POST http://127.0.0.1:8000/scenario/evaluate \
  -H 'content-type: application/json' \
  -d '{"rainfall_multiplier":1.5,"drainage_blockage_percent":40,"selected_cell_ids":["MUM-V2-01-01"],"scenario_name":"Demo"}'
```

The formula and band thresholds are in `backend/config/risk_model_v1.yaml`. Every response and evaluated cell reports `provenance: "synthetic"`.
