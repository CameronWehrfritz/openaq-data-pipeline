#!/usr/bin/env python3
"""
Test Simple BigQuery Insert
See if basic inserts work at all
"""

from datetime import datetime, timezone
from pipeline_config import PipelineConfig
from logger import PipelineLogger
from bigquery_manager import BigQueryManager

def test_simple_insert():
    """Test a very simple insert to see if BigQuery is working"""
    print("🧪 Testing Simple BigQuery Insert...")
    
    config = PipelineConfig()
    logger_setup = PipelineLogger(config)
    bq_manager = BigQueryManager(config)
    
    # Test insert to sensors table
    print(f"\n📊 Testing insert to sensors table...")
    
    # Create a simple test record
    test_sensor = {
        "sensor_id": "test_sensor_001",
        "location_id": "test_location_001", 
        "location_name": "Test Location",
        "locality": "Test City",
        "timezone": "America/Los_Angeles",
        "country_id": "840",
        "country_code": "US",
        "country_name": "United States",
        "owner_id": "test_owner",
        "owner_name": "Test Owner",
        "provider_id": "test_provider", 
        "provider_name": "Test Provider",
        "is_mobile": False,
        "is_monitor": True,
        "lat": 34.0522,
        "lon": -118.2437,
        "datetimeFirst": "2025-01-01T00:00:00Z",
        "datetimeLast": "2025-08-11T20:00:00Z",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    print(f"🔍 Test record: {test_sensor['sensor_id']} at ({test_sensor['lat']}, {test_sensor['lon']})")
    
    # Try inserting
    success = bq_manager.insert_rows(
        config.DATASET_ID,
        config.SENSOR_TABLE_ID,
        [test_sensor]
    )
    
    if success:
        print(f"✅ Insert reported SUCCESS")
        
        # Wait a moment for consistency
        import time
        print(f"⏳ Waiting 3 seconds for BigQuery consistency...")
        time.sleep(3)
        
        # Check if data actually exists
        print(f"🔍 Checking if data actually exists...")
        
        # Method 1: Check table row count
        table_info = bq_manager.get_table_info(config.DATASET_ID, config.SENSOR_TABLE_ID)
        if table_info:
            print(f"📊 Table row count: {table_info['num_rows']}")
            
        # Method 2: Query for our specific record
        test_query = f"""
        SELECT sensor_id, location_name, created_at
        FROM `{config.PROJECT_ID}.{config.DATASET_ID}.{config.SENSOR_TABLE_ID}`
        WHERE sensor_id = 'test_sensor_001'
        """
        
        result_df = bq_manager.execute_query(test_query)
        
        if result_df is not None and not result_df.empty:
            print(f"✅ SUCCESS! Found our test record:")
            for _, row in result_df.iterrows():
                print(f"   • {row['sensor_id']}: {row['location_name']} (created: {row['created_at']})")
        else:
            print(f"❌ PROBLEM! Insert succeeded but data not found")
            print(f"🔍 This suggests a streaming buffer or consistency issue")
            
        # Method 3: Try a simple count query
        count_query = f"""
        SELECT COUNT(*) as total_rows
        FROM `{config.PROJECT_ID}.{config.DATASET_ID}.{config.SENSOR_TABLE_ID}`
        """
        
        count_df = bq_manager.execute_query(count_query)
        if count_df is not None:
            total_rows = count_df.iloc[0]['total_rows']
            print(f"📊 Total rows via COUNT query: {total_rows}")
            
    else:
        print(f"❌ Insert reported FAILURE")
        return False
    
    return True

def test_job_tracking_insert():
    """Test insert to job tracking table"""
    print(f"\n📊 Testing insert to job tracking table...")
    
    config = PipelineConfig()
    bq_manager = BigQueryManager(config)
    
    # Create a simple test job record
    test_job = {
        "job_id": "test_job_001",
        "job_name": "Test Job",
        "start_time": datetime.now(timezone.utc).isoformat(),
        "status": "SUCCESS",
        "notes": "Test job for debugging",
        "error_message": None,
        "rows_inserted": 1,
        "duration_seconds": 10.5,
        "api_requests_made": 1,
        "sensors_processed": 1,
        "new_sensors_found": 1,
        "sensors_updated": 0,
        "data_quality_issues": 0,
        "pipeline_version": "1.0.0",
        "environment": "test"
    }
    
    print(f"🔍 Test job: {test_job['job_id']}")
    
    # Try inserting
    success = bq_manager.insert_rows(
        config.JOBS_DATASET_ID,
        config.JOBS_TABLE_ID,
        [test_job]
    )
    
    if success:
        print(f"✅ Job insert reported SUCCESS")
        
        # Check if it exists
        import time
        time.sleep(2)
        
        job_query = f"""
        SELECT job_id, job_name, status
        FROM `{config.PROJECT_ID}.{config.JOBS_DATASET_ID}.{config.JOBS_TABLE_ID}`
        WHERE job_id = 'test_job_001'
        """
        
        result_df = bq_manager.execute_query(job_query)
        
        if result_df is not None and not result_df.empty:
            print(f"✅ SUCCESS! Found our test job")
        else:
            print(f"❌ PROBLEM! Job insert succeeded but data not found")
            
    else:
        print(f"❌ Job insert reported FAILURE")

def cleanup_test_data():
    """Clean up test data"""
    print(f"\n🧹 Cleaning up test data...")
    
    config = PipelineConfig()
    bq_manager = BigQueryManager(config)
    
    # Delete test sensor
    delete_sensor_query = f"""
    DELETE FROM `{config.PROJECT_ID}.{config.DATASET_ID}.{config.SENSOR_TABLE_ID}`
    WHERE sensor_id = 'test_sensor_001'
    """
    
    # Delete test job
    delete_job_query = f"""
    DELETE FROM `{config.PROJECT_ID}.{config.JOBS_DATASET_ID}.{config.JOBS_TABLE_ID}`
    WHERE job_id = 'test_job_001'
    """
    
    try:
        bq_manager.execute_query(delete_sensor_query)
        bq_manager.execute_query(delete_job_query)
        print(f"✅ Test data cleaned up")
    except Exception as e:
        print(f"❌ Error cleaning up: {e}")

if __name__ == "__main__":
    print("🧪 BigQuery Insert Test Suite")
    print("=" * 40)
    
    # Test sensors table
    sensor_success = test_simple_insert()
    
    # Test job tracking table  
    test_job_tracking_insert()
    
    # Cleanup
    input("\nPress Enter to clean up test data...")
    cleanup_test_data()
    
    print(f"\n🎯 Test Summary:")
    if sensor_success:
        print(f"✅ Basic BigQuery functionality works")
        print(f"🔍 The issue is likely in your pipeline logic, not BigQuery itself")
    else:
        print(f"❌ Basic BigQuery inserts are failing")
        print(f"🔍 This suggests a permissions or configuration issue")