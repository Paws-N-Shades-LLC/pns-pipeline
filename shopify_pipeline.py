import os
import requests
import pandas as pd
from google.cloud import bigquery

SHOPIFY_STORE_DOMAIN = os.environ.get('SHOPIFY_STORE_DOMAIN', 'the-source-usa.myshopify.com')
SHOPIFY_ACCESS_TOKEN = os.environ.get('SHOPIFY_ACCESS_TOKEN')
BQ_PROJECT_ID = os.environ.get('BQ_PROJECT_ID')
BQ_DATASET_ID = os.environ.get('BQ_DATASET_ID', 'pns_core')

def shopify_request(endpoint):
    url = f"https://{SHOPIFY_STORE_DOMAIN}/admin/api/2024-01/{endpoint}"
    headers = {
        "X-Shopify-Access-Token": SHOPIFY_ACCESS_TOKEN,
        "Content-Type": "application/json"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching {endpoint}: {response.text}")
        return {}

def process_orders_and_related(orders_data):
    orders = []
    fulfillments = []
    refunds = []
    
    for order in orders_data:
        # Order Core
        orders.append({
            "order_id": str(order['id']),
            "order_number": str(order['order_number']),
            "created_at": order['created_at'],
            "total_price": float(order['total_price']),
            "financial_status": order.get('financial_status', ''),
            "fulfillment_status": order.get('fulfillment_status') or 'unfulfilled'
        })
        
        # Fulfillments
        for f in order.get('fulfillments', []):
            fulfillments.append({
                "fulfillment_id": str(f['id']),
                "order_id": str(order['id']),
                "status": f.get('status', ''),
                "created_at": f.get('created_at'),
                "location_id": str(f.get('location_id', '')),
                "tracking_company": f.get('tracking_company', '')
            })
            
        # Refunds
        for r in order.get('refunds', []):
            refunds.append({
                "refund_id": str(r['id']),
                "order_id": str(order['id']),
                "created_at": r.get('created_at'),
                "processed_at": r.get('processed_at')
            })
            
    return pd.DataFrame(orders), pd.DataFrame(fulfillments), pd.DataFrame(refunds)

def process_products(products_data):
    products = []
    for p in products_data:
        products.append({
            "product_id": str(p['id']),
            "title": p.get('title', ''),
            "vendor": p.get('vendor', ''),
            "product_type": p.get('product_type', ''),
            "status": p.get('status', '')
        })
    return pd.DataFrame(products)

def process_inventory(inventory_data):
    levels = []
    for i in inventory_data:
        levels.append({
            "inventory_item_id": str(i['inventory_item_id']),
            "location_id": str(i['location_id']),
            "available": i.get('available', 0),
            "updated_at": i.get('updated_at', '')
        })
    return pd.DataFrame(levels)

def load_to_bigquery(df, table_name):
    if df is None or df.empty:
        return
    client = bigquery.Client(project=BQ_PROJECT_ID)
    dataset_ref = client.dataset(BQ_DATASET_ID)
    try:
        client.get_dataset(dataset_ref)
    except Exception:
        client.create_dataset(bigquery.Dataset(dataset_ref))

    table_id = f"{BQ_PROJECT_ID}.{BQ_DATASET_ID}.{table_name}"
    job_config = bigquery.LoadJobConfig(write_disposition="WRITE_APPEND")
    try:
        job = client.load_table_from_dataframe(df, table_id, job_config=job_config)
        job.result() 
        print(f"Successfully loaded {len(df)} rows into {table_name}!")
    except Exception as e:
        print(f"Failed to load {table_name}: {str(e)}")

if __name__ == "__main__":
    print(f"Fetching Shopify data from {SHOPIFY_STORE_DOMAIN}...")
    
    # 1. Orders, Fulfillments, Refunds
    orders_resp = shopify_request("orders.json?status=any&limit=250")
    raw_orders = orders_resp.get('orders', [])
    df_orders, df_full, df_ref = process_orders_and_related(raw_orders)
    load_to_bigquery(df_orders, "shopify_orders")
    load_to_bigquery(df_full, "shopify_fulfillments")
    load_to_bigquery(df_ref, "shopify_refunds")
    
    # 2. Products
    prod_resp = shopify_request("products.json?limit=250")
    raw_products = prod_resp.get('products', [])
    df_prod = process_products(raw_products)
    load_to_bigquery(df_prod, "shopify_products")
    
    # 3. Inventory (Need locations first)
    loc_resp = shopify_request("locations.json")
    locations = loc_resp.get('locations', [])
    loc_ids = ",".join([str(l['id']) for l in locations])
    
    if loc_ids:
        inv_resp = shopify_request(f"inventory_levels.json?location_ids={loc_ids}&limit=250")
        raw_inv = inv_resp.get('inventory_levels', [])
        df_inv = process_inventory(raw_inv)
        load_to_bigquery(df_inv, "shopify_inventory")
