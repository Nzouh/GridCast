# IBM Code Engine Inference Job

This packages GridCast inference as a one-shot IBM Code Engine job:

```text
download runtime artifacts from COS
-> run TFT inference
-> apply quantile calibration
-> export frontend JSON
-> upload nodes/forecast/live JSON to COS
```

The web frontend keeps reading:

```env
GRIDCAST_DATA_SOURCE=cos
COS_BASE_URL=https://gridcast-artifacts.s3.us-east.cloud-object-storage.appdomain.cloud
```

## Runtime Artifacts

The container does not bake generated artifacts into Git or the image. Publish
them to COS first:

```powershell
.\.venv\Scripts\python.exe backend\models\sync_runtime_artifacts.py upload
```

This writes:

```text
artifacts/current/model/checkpoint.ckpt
artifacts/current/model/tft_calibration.json
artifacts/current/data/processed/all_nodes.parquet
artifacts/current/data/raw/weather_forecast_dominion_hub.parquet
artifacts/current/data/raw/weather_forecast_caiso_sp15.parquet
artifacts/current/data/raw/weather_forecast_caiso_np15.parquet
artifacts/current/data/raw/weather_forecast_ercot_houston.parquet
```

## Local Job Test

This is the same command the container runs:

```powershell
.\.venv\Scripts\python.exe backend\models\run_inference_pipeline.py
```

Expected result: 9 frontend JSON objects are uploaded to COS:

```text
nodes.json
forecast/{node_id}.json
live/{node_id}.json
```

## Container

Build locally:

```powershell
docker build -f Dockerfile.inference -t gridcast-inference:latest .
```

Run locally with your `.env`:

```powershell
docker run --env-file .env gridcast-inference:latest
```

## Code Engine

IBM's Code Engine CLI supports creating jobs from images or source, submitting
job runs, and passing environment variables with `--env`.

Typical flow:

```powershell
ibmcloud login
ibmcloud plugin install code-engine
ibmcloud ce project select --name <your-code-engine-project>
```

Create the job from source:

```powershell
ibmcloud ce job create `
  --name gridcast-inference `
  --build-source . `
  --build-dockerfile Dockerfile.inference `
  --build-size large `
  --cpu 2 `
  --memory 8G `
  --ephemeral-storage 4G `
  --env IBM_COS_API_KEY=<secret> `
  --env IBM_COS_RESOURCE_INSTANCE_ID=<secret> `
  --env IBM_COS_ENDPOINT=https://s3.us-east.cloud-object-storage.appdomain.cloud `
  --env IBM_COS_BUCKET=gridcast-artifacts `
  --env GRIDCAST_RUNTIME_ARTIFACT_PREFIX=artifacts/current `
  --env GRIDCAST_DOWNLOAD_RUNTIME_ARTIFACTS=true `
  --env GRIDCAST_COS_PUBLIC_READ=true `
  --env GRIDCAST_TFT_TRAIN_DAYS=365
```

Run on demand:

```powershell
ibmcloud ce jobrun submit --job gridcast-inference
```

For scheduled runs, create an IBM Code Engine subscription/event trigger from
the console or CLI after the job exists.

Do not put `.env`, checkpoints, parquet files, or `backend/models/out/` into
the container image. `.dockerignore` excludes them.
