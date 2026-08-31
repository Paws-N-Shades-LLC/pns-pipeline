import os
import requests
import pandas as pd
from google.cloud import bigquery
from datetime import datetime

# --- Configuration (Loaded from Railway Environment Variables) ---
SHOPIFY_STORE_DOMAIN = os.environ.get('SHOPIFY_STORE_DOMAIN', 'immmg-eq.myshopify.com')
SHOPIFY_ACCESS_TOKEN = os.environ.get('SHOPIFY_ACCESS_TOKEN') # We will generate this soon
BQ_PROJECT_ID = os.environ.get('BQ_PROJECT_ID')
BQ_DATASET_ID = os.environ.get('BQ_DATASET_ID', 'pns_core')

def get_shopify_orders():
    """Extracts recent orders and fulfillments from Shopify"""
    print(f"Fetching orders from {SHOPIFY_STORE_DOMAIN}...")
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    
    # We fetch the last 7 days of orders for incremental sync
    url = f"https://{SHOPIFY_STORE_DOMAIN}/admin/api/2024-01/orders.json?status=any&limit=250"
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"Error fetching Shopify data: {response.text}")
        return []

    orders = response.json().get('orders', [])
    print(f"Successfully extracted {len(orders)} orders.")
    return orders

def transform_orders(orders_data):
    """Transforms raw Shopify JSON into a flat Pandas DataFrame for BigQuery"""
    processed = []
    for order in orders_data:
        # We need to extract the fulfillment location to track which supplier shipped it!
        supplier_location = "Unknown"
        if order.get('fulfillments'):
            supplier_location = order['fulfillments'][0].get('location_id', 'Unknown')

        processed.append({
            "order_id": str(order['id']),
            "order_number": order['order_number'],
            "created_at": order['created_at'],
            "total_price": float(order['total_price']),
            "financial_status": order['financial_status'],
            "fulfillment_status": order['fulfillment_status'] or 'unfulfilled',
            "supplier_location_id": str(supplier_location)
        })
    
    return pd.DataFrame(processed)

def load_to_bigquery(df, table_name):
    """Pushes the Pandas DataFrame into Google BigQuery"""
    if df.empty:
        print(f"No data to load into {table_name}.")
        return

    print(f"Pushing {len(df)} records to BigQuery ({BQ_PROJECT_ID}.{BQ_DATASET_ID}.{table_name})...")
    
    client = bigquery.Client(project=BQ_PROJECT_ID)
    table_id = f"{BQ_PROJECT_ID}.{BQ_DATASET_ID}.{table_name}"
    
    # Configure the load job to overwrite or append
    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_APPEND", # Incremental load
    )
    
    try:
        job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result() # Wait for the job to complete
        print(f"Successfully loaded data into {table_id}!")
    except Exception as e:
        print(f"Failed to load to BigQuery: {str(e)}")

if __name__ == "__main__":
    print("=== Starting Shopify to BigQuery Pipeline ===")
    raw_orders = get_shopify_orders()
    if raw_orders:
        df_orders = transform_orders(raw_orders)
        load_to_bigquery(df_orders, "shopify_orders")
    print("=== Pipeline Complete ===")
