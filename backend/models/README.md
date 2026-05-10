# GridCast models

The demand model target is `demand_mw`. LMP data is used for economic
visualizations, not as the primary prediction target.

## Baseline

Run:

```powershell
.\.venv\Scripts\python.exe backend\models\baseline.py
```

Inputs:

- `backend/data/processed/all_nodes.parquet`

Outputs:

- `backend/models/out/baseline_metrics.csv`
- `backend/models/out/baseline_predictions.parquet`

Current 60-day holdout result using the 2024-2026 raw pull:

| Baseline | Overall MAPE | Overall MAE |
|---|---:|---:|
| 24h persistence | 5.243% | 739.81 MW |
| EIA day-ahead forecast | 7.521% | 1092.48 MW |
| 168h seasonal naive | 7.885% | 1136.28 MW |

The first TFT training pass should beat the 24h persistence baseline on the
same holdout window before we spend time packaging it for IBM.

## TFT

Install the ML stack:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-ml.txt
```

For local RTX 3060 training, make sure PyTorch is the CUDA build:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade --index-url https://download.pytorch.org/whl/cu128 torch torchvision torchaudio
```

Verify CUDA:

```powershell
.\.venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'none')"
```

Smoke-test the data/model plumbing:

```powershell
.\.venv\Scripts\python.exe backend\models\train_tft.py --fast-dev-run --batch-size 16
```

Run an initial bounded local training pass:

```powershell
.\.venv\Scripts\python.exe backend\models\train_tft.py --epochs 1 --batch-size 64 --train-days 180 --limit-train-batches 100 --limit-val-batches 20
```

Run a fuller GPU training pass locally, on Colab, or on IBM:

```powershell
.\.venv\Scripts\python.exe backend\models\train_tft.py --epochs 30 --batch-size 128 --num-workers 4
```

Evaluate a trained checkpoint:

```powershell
.\.venv\Scripts\python.exe backend\models\evaluate_tft.py --batch-size 64
```

Calibrate the TFT quantiles:

```powershell
.\.venv\Scripts\python.exe backend\models\calibrate_tft.py
```

Export frontend-ready COS payloads:

```powershell
.\.venv\Scripts\python.exe backend\models\export_forecasts.py --source cos
```

Upload exported payloads to IBM COS:

```powershell
.\.venv\Scripts\python.exe backend\models\upload_cos.py --public-read
```

The uploader writes these bucket-root objects, matching the current Next.js
`COS_BASE_URL` contract:

- `nodes.json`
- `forecast/{node_id}.json`
- `live/{node_id}.json`

For IBM Code Engine packaging, see `backend/models/CODE_ENGINE.md`.

Outputs:

- `backend/models/out/tft/checkpoints/`
- `backend/models/out/tft/logs/`
- `backend/models/out/tft/training_metadata.json`
- `backend/models/out/tft_eval_metrics.csv`
- `backend/models/out/tft_eval_by_horizon.csv`
- `backend/models/out/tft_eval_by_lead_hour.csv`
- `backend/models/out/tft_predictions.parquet`
- `backend/models/out/tft_calibration.json`
- `backend/models/out/tft_calibration_metrics.csv`
- `backend/models/out/tft_calibrated_predictions.parquet`
- `backend/models/out/cos_payload/`

Current setup:

- Target: `demand_mw`
- Joint model: one TFT across all 4 nodes, with `node_id` as a static categorical
- Encoder: 168 hours
- Decoder: 240 hours
- Quantiles: p10, p25, p50, p75, p90
- Known future inputs: weather and calendar features

Current first GPU run:

```powershell
.\.venv\Scripts\python.exe backend\models\train_tft.py --epochs 3 --batch-size 64 --train-days 365 --limit-val-batches 40 --num-workers 0
.\.venv\Scripts\python.exe backend\models\evaluate_tft.py --batch-size 64 --num-workers 0
```

Full rolling validation result:

| Model | Overall MAPE | Overall MAE |
|---|---:|---:|
| TFT p50 | 4.495% | 648.19 MW |
| 24h persistence | 5.226% | 737.03 MW |
| EIA day-ahead forecast | 7.566% | 1098.86 MW |
| 168h seasonal naive | 7.821% | 1124.80 MW |

The first rough TFT beats persistence overall, but its raw quantile bands are
too narrow: p10-p90 coverage is 58.12% instead of the nominal 80%.

Post-hoc calibration fixes the validation coverage:

| Interval | Before | After | Target |
|---|---:|---:|---:|
| p10-p90 coverage | 58.12% | 80.00% | 80% |
| p25-p75 coverage | 32.66% | 50.01% | 50% |

The calibration artifact stores per-node/per-horizon quantile corrections for
inference. For production, learn these corrections on a dedicated calibration
split rather than the same validation predictions used for reporting.
