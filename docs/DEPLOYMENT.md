# Release and deployment guide

VarshaVyuha is deployed as two services: a static Vite frontend on Vercel and a FastAPI API on Render **or** Railway. Do not use both backend hosts for the same production release.

## Environment variables

| Where | Variable | Value |
| --- | --- | --- |
| Render or Railway backend | `ALLOWED_FRONTEND_ORIGINS` | The complete deployed frontend origin, for example `https://your-project.vercel.app`. Multiple complete origins can be comma-separated. Local Vite origins remain allowed automatically. Do not use `*`, a path, or a trailing URL route. |
| Vercel frontend | `VITE_API_BASE_URL` | The complete public API origin, for example `https://your-api.onrender.com`. No trailing slash is required. |
| Vercel frontend (optional) | `VITE_MAPTILER_KEY` | A browser-safe MapTiler key. Omit it to keep the reliable offline-vector map only. |

`frontend/.env.local` and any other `.env*` file except the tracked `.env.example` templates are ignored by Git. Never put actual keys in a committed file.

## Deploy in this order

1. Run the release checks below and push the Git repository.
2. Create **one** API service from the repository:
   - **Render:** use `render.yaml`, set `ALLOWED_FRONTEND_ORIGINS` temporarily to the final Vercel URL once known, and confirm `/health` returns HTTP 200.
   - **Railway:** use `railway.json`, set the same variable, and confirm `/health` returns HTTP 200.
3. Copy the backend's public HTTPS URL.
4. Create a Vercel project from the same repository. `vercel.json` installs from `frontend/`, builds the Vite app, and serves `frontend/dist`.
5. Set `VITE_API_BASE_URL` to the backend HTTPS URL. Optionally set `VITE_MAPTILER_KEY` for Satellite + 3D context.
6. Deploy Vercel and copy its HTTPS URL.
7. Set or update `ALLOWED_FRONTEND_ORIGINS` on the selected API service to exactly that Vercel origin; redeploy the API after the environment change.
8. Reload the Vercel URL and complete the public smoke test below.

For a preview deployment, add that precise preview origin to `ALLOWED_FRONTEND_ORIGINS` as a second comma-separated value. Do not use an origin wildcard.

## Render and Railway settings

Both backend configurations start:

```bash
PYTHONPATH=backend uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

The app includes all required versioned `data/processed/`, `data/synthetic/`, `data/manifests/`, and `backend/config/` files in the Git repository. It does not need `data/raw/` at runtime.

## Vercel settings

The repository-root `vercel.json` uses:

```text
install: npm --prefix frontend ci
build:   npm --prefix frontend run build
output:  frontend/dist
```

The Vite `VITE_*` variables are embedded at build time. Change one in Vercel, then redeploy the frontend.

## GitHub first-commit commands

Create an empty GitHub repository named `varshavyuha` first, without adding a README, license, or `.gitignore`. Then run these commands from the repository root, replacing `YOUR_GITHUB_USERNAME`:

```bash
git add .
git status
git commit -m "Initial VarshaVyuha release"
git branch -M main
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/varshavyuha.git
git push -u origin main
```

Before committing, `git status` must not list `data/raw/`, `frontend/.env.local`, `node_modules/`, `frontend/dist/`, or a real provider key.

## Public smoke-test checklist

- [ ] Open the Vercel HTTPS URL. The prototype disclaimer and `SCENARIO ESTIMATE` badge are visible.
- [ ] Scenario Lab loads a 120-cell grid, local roads/water context, controls, and risk legend.
- [ ] Change rainfall/blockage, run the scenario, and click a cell. Verify the score details identify observed, derived, and synthetic drivers and never call it a prediction.
- [ ] Run Mitigation Simulator with a non-zero rainfall value and one intervention. Verify baseline, after-intervention modeled accumulation, and a non-negative modeled reduction.
- [ ] Open Historical Evidence. Verify observed IMD rainfall, its period/units/limitations, OSM attribution, and no scenario grid or risk score.
- [ ] With no `VITE_MAPTILER_KEY`, verify only Offline vector context works. With a configured valid key, select Satellite + 3D context and verify its reference-only note and attribution. Simulate a failed tile/style load and verify the automatic Offline vector fallback note.
- [ ] Clear the browser's VarshaVyuha local storage (or use a private window), verify the onboarding tour, then finish/skip it and verify it does not block map controls.
- [ ] Request `https://YOUR_API_HOST/health` and verify HTTP 200 plus `status: "ok"`.
