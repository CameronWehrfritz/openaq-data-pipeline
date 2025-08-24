#!/usr/bin/env python3
"""
BigQuery Table Schema Fix Script
Recreates the sensors table with the correct schema
"""

from pipeline_config import PipelineConfig
from logger import PipelineLogger
from bigquery_manager import BigQueryManager
from sensor_manager import SensorManager
from job_tracker import JobTracker

def fix_job_tracking_table():
    """Fix the job tracking table schema by recreating it properly"""
    print("FIXING: Fixing BigQuery Job Tracking Table Schema...")
    
    # Initialize components
    config = PipelineConfig()
    logger_setup = PipelineLogger(config)
    bq_manager = BigQueryManager(config)
    job_tracker = JobTracker(bq_manager, config)
    
    table_name = f"{config.PROJECT_ID}.{config.JOBS_DATASET_ID}.{config.JOBS_TABLE_ID}"
    
    print(f"TARGET: Target table: {table_name}")
    
    # Step 1: Check current table status
    print(f"\nSTEP 1: Step 1: Checking current job tracking table status...")
    table_exists = bq_manager.table_exists(config.JOBS_DATASET_ID, config.JOBS_TABLE_ID)
    
    if table_exists:
        print(f"SUCCESS: Job tracking table exists - checking current schema...")
        
        # Get current schema
        table_info = bq_manager.get_table_info(config.JOBS_DATASET_ID, config.JOBS_TABLE_ID)
        if table_info:
            print(f"INFO: Current schema ({table_info['num_rows']} rows):")
            for field in table_info['schema']:
                print(f"   • {field['name']}: {field['type']} ({field['mode']})")
            
            # Check if schema is correct
            current_fields = {field['name'] for field in table_info['schema']}
            required_fields = {field.name for field in job_tracker.job_schema}
            
            missing_fields = required_fields - current_fields
            extra_fields = current_fields - required_fields
            
            if missing_fields or extra_fields:
                print(f"\nWARNING: Job tracking schema issues detected:")
                if missing_fields:
                    print(f"   Missing fields: {missing_fields}")
                if extra_fields:
                    print(f"   Extra fields: {extra_fields}")
                
                # Ask for confirmation to delete
                print(f"\nWARNING:  Need to recreate job tracking table with correct schema.")
                print(f"DATA: Current table has {table_info['num_rows']} job records that will be lost.")
                
                confirm = input("CONFIRM: Proceed with job tracking table recreation? (yes/no): ").lower().strip()
                if confirm not in ['yes', 'y']:
                    print("WARNING: Aborted by user")
                    return False
                
                # Step 2: Delete old table
                print(f"\nDELETE:  Step 2: Deleting old job tracking table...")
                if bq_manager.delete_table(config.JOBS_DATASET_ID, config.JOBS_TABLE_ID):
                    print(f"SUCCESS: Old job tracking table deleted successfully")
                else:
                    print(f"WARNING: Failed to delete old job tracking table")
                    return False
            else:
                print(f"SUCCESS: Current job tracking schema is correct!")
                return True
    else:
        print(f"INFO: Job tracking table doesn't exist - will create new one")
    
    # Step 3: Create new table with correct schema
    print(f"\nCREATE: Step 3: Creating job tracking table with correct schema...")
    
    print(f"INFO: New job tracking schema will include:")
    for field in job_tracker.job_schema:
        print(f"   • {field.name}: {field.field_type} ({field.mode}) - {field.description}")
    
    success = job_tracker.ensure_job_tracking_table_exists()
    
    if success:
        print(f"SUCCESS: Job tracking table created successfully!")
        
        # Step 4: Verify new schema
        print(f"\nVERIFY: Step 4: Verifying new job tracking schema...")
        table_info = bq_manager.get_table_info(config.JOBS_DATASET_ID, config.JOBS_TABLE_ID)
        
        if table_info:
            print(f"STEP 1: Verified job tracking schema:")
            for field in table_info['schema']:
                print(f"   • {field['name']}: {field['type']} ({field['mode']})")
            
            # Check all required fields are present
            current_fields = {field['name'] for field in table_info['schema']}
            required_fields = {field.name for field in job_tracker.job_schema}
            
            if required_fields.issubset(current_fields):
                print(f"\nCOMPLETE: SUCCESS! Job tracking table schema is now correct.")
                print(f"TARGET: Table ready for job tracking.")
                return True
            else:
                missing = required_fields - current_fields
                print(f"\nWARNING: Job tracking schema verification failed - still missing: {missing}")
                return False
        else:
            print(f"WARNING: Could not verify new job tracking table schema")
            return False
    else:
        print(f"WARNING: Failed to create new job tracking table")
        return False


def fix_sensors_table():
    """Fix the sensors table schema by recreating it properly"""
    print("FIXING: Fixing BigQuery Sensors Table Schema...")
    
    # Initialize components
    config = PipelineConfig()
    logger_setup = PipelineLogger(config)
    bq_manager = BigQueryManager(config)
    sensor_manager = SensorManager(bq_manager, config)
    
    table_name = f"{config.PROJECT_ID}.{config.DATASET_ID}.{config.SENSOR_TABLE_ID}"
    
    print(f"TARGET: Target table: {table_name}")
    
    # Step 1: Check current table status
    print(f"\nSTEP 1: Step 1: Checking current table status...")
    table_exists = bq_manager.table_exists(config.DATASET_ID, config.SENSOR_TABLE_ID)
    
    if table_exists:
        print(f"SUCCESS: Table exists - checking current schema...")
        
        # Get current schema
        table_info = bq_manager.get_table_info(config.DATASET_ID, config.SENSOR_TABLE_ID)
        if table_info:
            print(f"INFO: Current schema ({table_info['num_rows']} rows):")
            for field in table_info['schema']:
                print(f"   • {field['name']}: {field['type']} ({field['mode']})")
            
            # Check if schema is correct
            current_fields = {field['name'] for field in table_info['schema']}
            required_fields = {field.name for field in sensor_manager.sensor_schema}
            
            missing_fields = required_fields - current_fields
            extra_fields = current_fields - required_fields
            
            if missing_fields or extra_fields:
                print(f"\nWARNING: Schema issues detected:")
                if missing_fields:
                    print(f"   Missing fields: {missing_fields}")
                if extra_fields:
                    print(f"   Extra fields: {extra_fields}")
                
                # Ask for confirmation to delete
                print(f"\nWARNING:  Need to recreate table with correct schema.")
                print(f"DATA: Current table has {table_info['num_rows']} rows that will be lost.")
                
                confirm = input("CONFIRM: Proceed with table recreation? (yes/no): ").lower().strip()
                if confirm not in ['yes', 'y']:
                    print("WARNING: Aborted by user")
                    return False
                
                # Step 2: Delete old table
                print(f"\nDELETE:  Step 2: Deleting old table...")
                if bq_manager.delete_table(config.DATASET_ID, config.SENSOR_TABLE_ID):
                    print(f"SUCCESS: Old table deleted successfully")
                else:
                    print(f"WARNING: Failed to delete old table")
                    return False
            else:
                print(f"SUCCESS: Current schema is correct!")
                return True
    else:
        print(f"INFO: Table doesn't exist - will create new one")
    
    # Step 3: Create new table with correct schema
    print(f"\nCREATE: Step 3: Creating table with correct schema...")
    
    print(f"INFO: New schema will include:")
    for field in sensor_manager.sensor_schema:
        print(f"   • {field.name}: {field.field_type} ({field.mode}) - {field.description}")
    
    success = sensor_manager.ensure_sensors_table_exists()
    
    if success:
        print(f"SUCCESS: Table created successfully!")
        
        # Step 4: Verify new schema
        print(f"\nVERIFY: Step 4: Verifying new schema...")
        table_info = bq_manager.get_table_info(config.DATASET_ID, config.SENSOR_TABLE_ID)
        
        if table_info:
            print(f"STEP 1: Verified schema:")
            for field in table_info['schema']:
                print(f"   • {field['name']}: {field['type']} ({field['mode']})")
            
            # Check all required fields are present
            current_fields = {field['name'] for field in table_info['schema']}
            required_fields = {field.name for field in sensor_manager.sensor_schema}
            
            if required_fields.issubset(current_fields):
                print(f"\nCOMPLETE: SUCCESS! Table schema is now correct.")
                print(f"TARGET: Table ready for sensor data insertion.")
                return True
            else:
                missing = required_fields - current_fields
                print(f"\nWARNING: Schema verification failed - still missing: {missing}")
                return False
        else:
            print(f"WARNING: Could not verify new table schema")
            return False
    else:
        print(f"WARNING: Failed to create new table")
        return False

def show_correct_schema():
    """Show what the correct schema should look like"""
    print("TARGET: CORRECT SCHEMA SPECIFICATION:")
    print("=" * 60)
    
    config = PipelineConfig()
    bq_manager = BigQueryManager(config)
    sensor_manager = SensorManager(bq_manager, config)
    
    for field in sensor_manager.sensor_schema:
        mode_desc = "REQUIRED" if field.mode == "REQUIRED" else "OPTIONAL"
        print(f"{field.name:20} {field.field_type:12} {mode_desc:10} {field.description}")

def check_job_table_status():
    """Just check the current job tracking table status without making changes"""
    print("VERIFY: Checking Current Job Tracking Table Status...")
    
    config = PipelineConfig()
    logger_setup = PipelineLogger(config)
    bq_manager = BigQueryManager(config)
    
    table_exists = bq_manager.table_exists(config.JOBS_DATASET_ID, config.JOBS_TABLE_ID)
    
    if table_exists:
        table_info = bq_manager.get_table_info(config.JOBS_DATASET_ID, config.JOBS_TABLE_ID)
        if table_info:
            print(f"SUCCESS: Job tracking table exists with {table_info['num_rows']} rows")
            print(f"CREATED: {table_info['created']}")
            print(f"INFO: Current schema:")
            for field in table_info['schema']:
                print(f"   • {field['name']}: {field['type']} ({field['mode']})")
        else:
            print(f"WARNING: Job tracking table exists but could not get info")
    else:
        print(f"WARNING: Job tracking table does not exist")


def check_table_status():
    """Just check the current table status without making changes"""
    print("VERIFY: Checking Current Table Status...")
    
    config = PipelineConfig()
    logger_setup = PipelineLogger(config)
    bq_manager = BigQueryManager(config)
    
    table_exists = bq_manager.table_exists(config.DATASET_ID, config.SENSOR_TABLE_ID)
    
    if table_exists:
        table_info = bq_manager.get_table_info(config.DATASET_ID, config.SENSOR_TABLE_ID)
        if table_info:
            print(f"SUCCESS: Table exists with {table_info['num_rows']} rows")
            print(f"CREATED: {table_info['created']}")
            print(f"INFO: Current schema:")
            for field in table_info['schema']:
                print(f"   • {field['name']}: {field['type']} ({field['mode']})")
        else:
            print(f"WARNING: Table exists but could not get info")
    else:
        print(f"WARNING: Table does not exist")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        if sys.argv[1] == "--check":
            check_table_status()
        elif sys.argv[1] == "--check-jobs":
            check_job_table_status()
        elif sys.argv[1] == "--schema":
            show_correct_schema()
        elif sys.argv[1] == "--fix":
            fix_sensors_table()
        elif sys.argv[1] == "--fix-jobs":
            fix_job_tracking_table()
        else:
            print("Usage:")
            print("  python fix_bigquery_schema.py --check       # Check sensors table")
            print("  python fix_bigquery_schema.py --check-jobs  # Check job tracking table")
            print("  python fix_bigquery_schema.py --schema      # Show correct schema")
            print("  python fix_bigquery_schema.py --fix         # Fix sensors table")
            print("  python fix_bigquery_schema.py --fix-jobs    # Fix job tracking table")
    else:
        print("FIXING: BigQuery Table Schema Fix Tool")
        print("=" * 40)
        print("Options:")
        print("1. Check sensors table status")
        print("2. Check job tracking table status")
        print("3. Show correct schema specification")  
        print("4. Fix sensors table schema (DESTRUCTIVE)")
        print("5. Fix job tracking table schema (DESTRUCTIVE)")
        
        choice = input("\nChoose option (1-5): ").strip()
        
        if choice == "1":
            check_table_status()
        elif choice == "2":
            check_job_table_status()
        elif choice == "3":
            show_correct_schema()
        elif choice == "4":
            fix_sensors_table()
        elif choice == "5":
            fix_job_tracking_table()
        else:
            print("Invalid choice")