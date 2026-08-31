# PNS Data Warehouse Pipeline

This repository contains the Python scripts to extract data from Shopify and Gorgias and push it into Google BigQuery.

## How to Deploy on Railway
1. Push this folder to a GitHub repository.
2. Log into Railway and create a new project -> "Deploy from GitHub repo".
3. Add the following Environment Variables to the Railway project:
   - `SHOPIFY_STORE_DOMAIN`
   - `SHOPIFY_ACCESS_TOKEN`
   - `GORGIAS_DOMAIN`
   - `GORGIAS_EMAIL`
   - `GORGIAS_API_KEY`
   - `BQ_PROJECT_ID`
   - `BQ_DATASET_ID`
   - `GOOGLE_APPLICATION_CREDENTIALS` (The JSON key for the Service Account)

## Scripts
- `shopify_pipeline.py`: Pulls Orders and Fulfillments to track supplier metrics.
- `gorgias_pipeline.py`: Pulls Support Tickets to track customer sentiment and volume.

Both scripts use Pandas to flatten the data and load it into BigQuery via `WRITE_APPEND` for incremental tracking.
