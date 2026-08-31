import time
import schedule
import subprocess

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
