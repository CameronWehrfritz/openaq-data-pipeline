#!/usr/bin/env python3
"""
Simple cleanup script for BigQuery sensor data
"""

from pipeline_config import PipelineConfig
from bigquery_manager import BigQueryManager
from logger import PipelineLogger

def cleanup_data():
    """Clean up test data and duplicates"""
    print("🧹 Cleaning up BigQuery data...")
    
    config = PipelineConfig()
    logger_setup = PipelineLogger(config)
    bq_manager = BigQueryManager(config)
    
    # Step 1: Check current status
    print("\n📊 Current status:")
    count_query = f"""
    SELECT 
        COUNT(*) as total_rows,
        COUNT(DISTINCT sensor_id) as unique_sensors
    FROM `{config.PROJECT_ID}.{config.DATASET_ID}.{config.SENSOR_TABLE_ID}`
    """
    
    result = bq_manager.execute_query(count_query)
    if result is not None:
        total = result.iloc[0]['total_rows']
        unique = result.iloc[0]['unique_sensors']
        print(f"   Total rows: {total}")
        print(f"   Unique sensors: {unique}")
        
        if total == unique:
            print("✅ No cleanup needed - data is already clean!")
            return
    
    # Step 2: Remove test sensor
    print("\n🗑️  Step 1: Removing test sensor...")
    delete_test_query = f"""
    DELETE FROM `{config.PROJECT_ID}.{config.DATASET_ID}.{config.SENSOR_TABLE_ID}`
    WHERE sensor_id = 'test_sensor_001'
    """
    
    try:
        bq_manager.execute_query(delete_test_query)
        print("✅ Test sensor removed")
    except Exception as e:
        print(f"❌ Error removing test sensor: {e}")
    
    # Step 3: Remove duplicates (keep most recent)
    print("\n🗑️  Step 2: Removing duplicate sensors...")
    
    # First, let's see what duplicates we have
    duplicate_check_query = f"""
    SELECT 
        sensor_id,
        COUNT(*) as count
    FROM `{config.PROJECT_ID}.{config.DATASET_ID}.{config.SENSOR_TABLE_ID}`
    GROUP BY sensor_id
    HAVING COUNT(*) > 1
    ORDER BY count DESC
    """
    
    duplicates = bq_manager.execute_query(duplicate_check_query)
    if duplicates is not None and not duplicates.empty:
        print(f"   Found {len(duplicates)} sensors with duplicates:")
        for _, row in duplicates.head().iterrows():
            print(f"      • {row['sensor_id']}: {row['count']} copies")
        
        # Remove duplicates - keep the one with the latest created_at
        dedupe_query = f"""
        DELETE FROM `{config.PROJECT_ID}.{config.DATASET_ID}.{config.SENSOR_TABLE_ID}`
        WHERE (sensor_id, created_at) NOT IN (
            SELECT sensor_id, MAX(created_at) as latest_created
            FROM `{config.PROJECT_ID}.{config.DATASET_ID}.{config.SENSOR_TABLE_ID}`
            GROUP BY sensor_id
        )
        """
        
        try:
            bq_manager.execute_query(dedupe_query)
            print("✅ Duplicates removed (kept most recent)")
        except Exception as e:
            print(f"❌ Error removing duplicates: {e}")
    else:
        print("✅ No duplicates found")
    
    # Step 4: Final verification
    print("\n📊 Final status:")
    final_result = bq_manager.execute_query(count_query)
    if final_result is not None:
        final_total = final_result.iloc[0]['total_rows']
        final_unique = final_result.iloc[0]['unique_sensors']
        print(f"   Total rows: {final_total}")
        print(f"   Unique sensors: {final_unique}")
        
        if final_total == final_unique:
            print("🎉 SUCCESS! Data is now clean.")
        else:
            print("⚠️  Still have some duplicates or issues")

if __name__ == "__main__":
    cleanup_data()