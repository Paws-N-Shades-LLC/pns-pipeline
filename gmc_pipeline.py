import os
import pandas as pd
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.cloud import bigquery

MERCHANT_ID = os.environ.get('MERCHANT_ID', '5829285869')
BQ_PROJECT_ID = os.environ.get('BQ_PROJECT_ID')
BQ_DATASET_ID = os.environ.get('BQ_DATASET_ID', 'pns_core')

def get_gmc_issues():
    print(f"Fetching Google Merchant Center diagnostics for {MERCHANT_ID}...")
    try:
        # It automatically picks up GOOGLE_APPLICATION_CREDENTIALS from main.py
        service = build('content', 'v2.1')
        request = service.productstatuses().list(merchantId=MERCHANT_ID)
        
        all_issues = []
        while request is not None:
            result = request.execute()
            statuses = result.get('resources', [])
            
            for status in statuses:
                product_id = status.get('productId')
                title = status.get('title')
                issues = status.get('itemLevelIssues', [])
                
                for issue in issues:
                    all_issues.append({
                        "product_id": product_id,
                        "title": title,
                        "issue_code": issue.get('code'),
                        "description": issue.get('description'),
                        "resolution": issue.get('resolution'),
                        "destination": issue.get('destination'),
                        "servability": issue.get('servability')
                    })
                    
            request = service.productstatuses().list_next(request, result)
            
        print(f"Successfully extracted {len(all_issues)} GMC product issues.")
        return all_issues
    except Exception as e:
        print(f"Error fetching GMC data: {str(e)}")
        return []

def load_to_bigquery(df, table_name):
    if df.empty:
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
        print(f"Successfully loaded data into {table_id}!")
    except Exception as e:
        print(f"Failed to load to BigQuery: {str(e)}")

if __name__ == "__main__":
    raw_issues = get_gmc_issues()
    if raw_issues:
        df_issues = pd.DataFrame(raw_issues)
        load_to_bigquery(df_issues, "gmc_diagnostics")
