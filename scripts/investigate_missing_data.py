#!/usr/bin/env python3
"""
Investigate Missing Data Mystery
Find out where the 59 sensors went!
"""

from pipeline_config import PipelineConfig
from logger import PipelineLogger
from bigquery_manager import BigQueryManager

def investigate_missing_data():
    """Investigate where the data went"""
    print("🕵️ Investigating Missing Data Mystery...")
    
    config = PipelineConfig()
    logger_setup = PipelineLogger(config)
    bq_manager = BigQueryManager(config)
    
    print(f"🔍 Configuration:")
    print(f"   Project ID: {config.PROJECT_ID}")
    print(f"   Dataset ID: {config.DATASET_ID}")
    print(f"   Table ID: {config.SENSOR_TABLE_ID}")
    print(f"   Full table name: {config.PROJECT_ID}.{config.DATASET_ID}.{config.SENSOR_TABLE_ID}")
    
    # Check all datasets in the project
    print(f"\n📊 Checking all datasets in project...")
    try:
        datasets = list(bq_manager.client.list_datasets())
        print(f"Found {len(datasets)} datasets:")
        
        for dataset in datasets:
            print(f"   • {dataset.dataset_id}")
            
            # Check tables in each dataset
            try:
                tables = list(bq_manager.client.list_tables(dataset.dataset_id))
                for table in tables:
                    table_ref = f"{config.PROJECT_ID}.{dataset.dataset_id}.{table.table_id}"
                    table_info = bq_manager.client.get_table(table_ref)
                    print(f"      └─ {table.table_id}: {table_info.num_rows} rows")
                    
                    # If this looks like a sensor table with data, investigate
                    if table_info.num_rows > 0 and ("sensor" in table.table_id.lower() or "pm25" in table.table_id.lower()):
                        print(f"         🔍 This might be our data!")
                        
                        # Get a sample of the data
                        sample_query = f"""
                        SELECT sensor_id, location_name, created_at, updated_at
                        FROM `{table_ref}`
                        LIMIT 5
                        """
                        
                        try:
                            sample_df = bq_manager.execute_query(sample_query)
                            if sample_df is not None and not sample_df.empty:
                                print(f"         📋 Sample data:")
                                for _, row in sample_df.iterrows():
                                    print(f"            • {row['sensor_id']}: {row['location_name']}")
                        except Exception as e:
                            print(f"         ❌ Error reading sample: {e}")
                            
            except Exception as e:
                print(f"      ❌ Error listing tables: {e}")
                
    except Exception as e:
        print(f"❌ Error listing datasets: {e}")
    
    # Check specifically for the expected table
    print(f"\n🎯 Checking specific target table...")
    target_table = f"{config.PROJECT_ID}.{config.DATASET_ID}.{config.SENSOR_TABLE_ID}"
    
    try:
        table = bq_manager.client.get_table(target_table)
        print(f"✅ Target table exists:")
        print(f"   Rows: {table.num_rows}")
        print(f"   Created: {table.created}")
        print(f"   Modified: {table.modified}")
        
        if table.num_rows == 0:
            print(f"❓ Table is empty - checking recent operations...")
            
            # Check table metadata for recent operations
            print(f"   Table description: {table.description}")
            print(f"   Schema fields: {len(table.schema)}")
            
            # Try to see if there are any traces of data
            history_query = f"""
            SELECT 
                CURRENT_TIMESTAMP() as current_time,
                '{target_table}' as table_name
            """
            
            result = bq_manager.execute_query(history_query)
            if result is not None:
                print(f"   Current BigQuery time: {result.iloc[0]['current_time']}")
                
    except Exception as e:
        print(f"❌ Target table not found or error: {e}")
    
    # Check job history for clues
    print(f"\n📈 Checking job tracking for clues...")
    try:
        jobs_table = f"{config.PROJECT_ID}.{config.JOBS_DATASET_ID}.{config.JOBS_TABLE_ID}"
        
        jobs_query = f"""
        SELECT job_id, job_name, status, start_time, rows_inserted, notes
        FROM `{jobs_table}`
        ORDER BY start_time DESC
        LIMIT 5
        """
        
        jobs_df = bq_manager.execute_query(jobs_query)
        if jobs_df is not None and not jobs_df.empty:
            print(f"📋 Recent job history:")
            for _, job in jobs_df.iterrows():
                print(f"   • {job['job_id']}: {job['status']} - {job['rows_inserted']} rows")
        else:
            print(f"❌ No job history found")
            
    except Exception as e:
        print(f"❌ Error checking job history: {e}")

if __name__ == "__main__":
    investigate_missing_data()