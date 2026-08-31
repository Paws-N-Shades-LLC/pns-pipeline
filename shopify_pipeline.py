import os
import requests
import pandas as pd
from google.cloud import bigquery
from datetime import datetime

# --- Configuration ---
SHOPIFY_STORE_DOMAIN = os.environ.get('SHOPIFY_STORE_DOMAIN', 'immmg-eq.myshopify.com')
SHOPIFY_ACCESS_TOKEN = os.environ.get('SHOPIFY_ACCESS_TOKEN')
BQ_PROJECT_ID = os.environ.get('BQ_PROJECT_ID')
BQ_DATASET_ID = os.environ.get('BQ_DATASET_ID', 'pns_core')

def get_shopify_orders():
    print(f"Fetching orders from {SHOPIFY_STORE_DOMAIN}...")
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    url = f"https://{SHOPIFY_STORE_DOMAIN}/admin/api/2024-01/orders.json?status=any&limit=250"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        print(f"Error fetching Shopify data: {response.text}")
        return []
    orders = response.json().get('orders', [])
    print(f"Successfully extracted {len(orders)} orders.")
    return orders

def transform_orders(orders_data):
    processed = []
    for order in orders_data:
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
    if df.empty:
        return
    client = bigquery.Client(project=BQ_PROJECT_ID)
    
    # Create dataset if it doesn't exist
    dataset_ref = client.dataset(BQ_DATASET_ID)
    try:
        client.get_dataset(dataset_ref)
    except Exception:
        print(f"Dataset {BQ_DATASET_ID} not found. Creating it...")
        client.create_dataset(bigquery.Dataset(dataset_ref))

    table_id = f"{BQ_PROJECT_ID}.{BQ_DATASET_ID}.{table_name}"
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    try:
        job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result() 
        print(f"Successfully loaded data into {table_id}!")
    except Exception as e:
        print(f"Failed to load to BigQuery: {str(e)}")

if __name__ == "__main__":
    raw_orders = get_shopify_orders()
    if raw_orders:
        df_orders = transform_orders(raw_orders)
        load_to_bigquery(df_orders, "shopify_orders")
