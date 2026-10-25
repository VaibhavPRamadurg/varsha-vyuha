# Dataset manifests

Each JSON manifest describes exactly one versioned artifact. The verifier checks the required provenance fields, allowed `source_type`, referenced file location, and SHA-256 checksum.

`data/raw/` contains untouched downloads and is intentionally Git-ignored. Its manifest is versioned so another team member can reproduce the acquisition. Processed artifacts belong in `data/processed/`; artificial demo inputs and outputs belong in `data/synthetic/` and must use `source_type: "synthetic"`.

Run from the repository root:

```bash
python3 scripts/acquire_mumbai_reference_data.py --synthetic-only
python3 scripts/verify_data_manifests.py
```

Remove `--synthetic-only` only when the official BMC service returns a valid, certificate-verifiable GeoJSON response. The BMC flooding-spots layer is a location/hotspot reference layer only: the service does not provide event timestamps or water-depth measurements, and it must not be represented as a real-time flood observation or forecast.
