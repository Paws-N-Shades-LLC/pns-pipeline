import os
import time
import schedule
import subprocess

# Write the Google JSON Key from the Environment Variable to a temporary file
if 'GOOGLE_JSON_KEY' in os.environ:
    creds_path = '/tmp/google_creds.json'
    # Fallback for Windows local testing
    if os.name == 'nt':
        creds_path = 'google_creds.json'
        
    with open(creds_path, 'w') as f:
        f.write(os.environ['GOOGLE_JSON_KEY'])
    
    # Tell the Google Cloud library where to find the key file
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = creds_path
    print("Successfully loaded Google Cloud credentials.")

def run_shopify():
    print("Running Shopify Pipeline...")
    subprocess.run(["python", "shopify_pipeline.py"])

def run_gorgias():
    print("Running Gorgias Pipeline...")
    subprocess.run(["python", "gorgias_pipeline.py"])

def run_all():
    print("--- Starting Full Pipeline Sync ---")
    run_shopify()
    run_gorgias()
    print("--- Sync Complete ---")

# Run immediately on startup
run_all()

# Schedule to run every hour
schedule.every(1).hours.do(run_all)

print("Scheduler started. Pipelines will run every 1 hour.")

while True:
    schedule.run_pending()
    time.sleep(60)
