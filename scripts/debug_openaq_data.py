#!/usr/bin/env python3
"""
Debug Script for OpenAQ Data Issues
Helps diagnose timestamp format and schema problems
"""

import sys
import json
from pipeline_config import PipelineConfig
from logger import PipelineLogger
from bigquery_manager import BigQueryManager
from openaq_client import OpenAQClient

def debug_api_response(large_sample=False):
    """Debug the actual OpenAQ API response format"""
    print("🔍 Debugging OpenAQ API Response Format...")
    
    config = PipelineConfig()
    if large_sample:
        config.API_REQUEST_LIMIT = 100  # Larger sample
        print("Using LARGE sample (100 locations per page)")
    else:
        config.API_REQUEST_LIMIT = 5   # Small sample for debugging
        print("Using small sample (5 locations per page)")
    
    logger_setup = PipelineLogger(config)
    client = OpenAQClient(config)
    
    # Fetch a sample
    sensors_df = client.fetch_pm25_ca_sensors()
    
    if not sensors_df.empty:
        print(f"\n✅ Fetched {len(sensors_df)} sensors for debugging")
        
        # Look at the first sensor's timestamps
        first_sensor = sensors_df.iloc[0]
        
        print(f"\n📋 Sample Sensor Data:")
        print(f"Sensor ID: {first_sensor['sensor_id']}")
        print(f"Location: {first_sensor['location_name']}")
        
        print(f"\n⏰ Timestamp Analysis:")
        print(f"datetimeFirst type: {type(first_sensor['datetimeFirst'])}")
        print(f"datetimeFirst value: {first_sensor['datetimeFirst']}")
        print(f"datetimeLast type: {type(first_sensor['datetimeLast'])}")  
        print(f"datetimeLast value: {first_sensor['datetimeLast']}")
        
        # If it's a dict, show the structure
        if isinstance(first_sensor['datetimeFirst'], dict):
            print(f"\n📊 Timestamp Dictionary Structure:")
            print(json.dumps(first_sensor['datetimeFirst'], indent=2))
        
        # Show all columns and their types
        print(f"\n📝 All Columns and Types:")
        for col in sensors_df.columns:
            sample_val = first_sensor[col]
            print(f"  {col}: {type(sample_val)} = {sample_val}")
    
    else:
        print("❌ No sensors fetched")
        print("This could mean:")
        print("1. No California sensors in the small sample (try --large-sample)")
        print("2. API response format changed")
        print("3. Geographic filtering is too restrictive")

def debug_bigquery_table():
    """Debug BigQuery table schema"""
    print("\n🔍 Debugging BigQuery Table Schema...")
    
    config = PipelineConfig()
    logger_setup = PipelineLogger(config)
    bq_manager = BigQueryManager(config)
    
    # Check if table exists
    table_exists = bq_manager.table_exists(config.DATASET_ID, config.SENSOR_TABLE_ID)
    print(f"Table exists: {table_exists}")
    
    if table_exists:
        # Get table info
        table_info = bq_manager.get_table_info(config.DATASET_ID, config.SENSOR_TABLE_ID)
        
        if table_info:
            print(f"\n📊 Current Table Schema:")
            print(f"Rows: {table_info['num_rows']}")
            print(f"Created: {table_info['created']}")
            
            print(f"\n📋 Schema Fields:")
            for field in table_info['schema']:
                print(f"  {field['name']}: {field['type']} ({field['mode']})")
        else:
            print("❌ Could not get table info")
    else:
        print("ℹ️ Table doesn't exist yet")

def suggest_fixes():
    """Suggest fixes based on the issues found"""
    config = PipelineConfig()  # Define config here
    
    print(f"\n🔧 Suggested Fixes:")
    print(f"1. OpenAQ timestamp format changed - updated _format_timestamp_for_bq() to handle dict format")
    print(f"2. Table schema is WRONG - missing fields and wrong types:")
    print(f"   Current table is missing: datetimeFirst, created_at, updated_at")
    print(f"   sensor_id and location_id should be STRING not INTEGER")
    print(f"3. DELETE and recreate table:")
    print(f"   - Go to BigQuery Console")
    print(f"   - Delete table: {config.PROJECT_ID}.{config.DATASET_ID}.{config.SENSOR_TABLE_ID}")
    print(f"   - Re-run pipeline to create table with correct schema")
    print(f"4. Or run: python debug_openaq_data.py --fix-table")
    print(f"5. Try with larger sample: python debug_openaq_data.py --large-sample")

def fix_table():
    """Delete and recreate the table"""
    config = PipelineConfig()
    logger_setup = PipelineLogger(config)
    bq_manager = BigQueryManager(config)
    
    print(f"🗑️ Deleting existing table...")
    if bq_manager.delete_table(config.DATASET_ID, config.SENSOR_TABLE_ID):
        print(f"✅ Table deleted successfully")
        print(f"ℹ️ Run your main pipeline again to recreate with correct schema")
    else:
        print(f"❌ Failed to delete table")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--fix-table":
        fix_table()
    elif len(sys.argv) > 1 and sys.argv[1] == "--large-sample":
        debug_api_response(large_sample=True)
        debug_bigquery_table()  
        suggest_fixes()
    else:
        debug_api_response(large_sample=False)
        debug_bigquery_table()  
        suggest_fixes()