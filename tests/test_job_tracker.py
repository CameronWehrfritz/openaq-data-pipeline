"""
Unit tests for Job Tracker
"""

import sys
import pandas as pd
from pathlib import Path
import pytest
from datetime import datetime

# Add scripts directory to path
scripts_path = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_path))

from job_tracker import JobTracker
from bigquery_manager import BigQueryManager
from pipeline_config import PipelineConfig


def test_job_tracker_event_based_tracking():
    """Test that job tracker creates both START and END events without UPDATE operations"""
    
    # Initialize components
    config = PipelineConfig()
    bq_manager = BigQueryManager(config)
    job_tracker = JobTracker(bq_manager, config)
    
    # Start a test job
    job_id = job_tracker.start_job("Test_Job_Event_Based", environment="testing")
    
    # Verify job_id was generated
    assert job_id is not None
    assert job_id.startswith("job_")
    assert job_tracker.get_current_job_id() == job_id
    
    # End the job
    success = job_tracker.end_job(
        status="SUCCESS",
        notes="Test completed",
        rows_inserted=10
    )
    
    assert success == True
    
    # Query BigQuery to verify both events exist
    query = f"""
    SELECT event_type, status, duration_seconds
    FROM `{config.PROJECT_ID}.{config.JOBS_DATASET_ID}.{config.JOBS_TABLE_ID}`
    WHERE job_id = '{job_id}'
    ORDER BY event_time
    """
    
    result_df = bq_manager.execute_query(query)
    
    # Verify we got 2 events
    assert len(result_df) == 2
    
    # Verify START event
    start_event = result_df.iloc[0]
    assert start_event['event_type'] == 'START'
    assert start_event['status'] == 'RUNNING'
    assert pd.isna(start_event['duration_seconds'])

    # Verify END event
    end_event = result_df.iloc[1]
    assert end_event['event_type'] == 'END'
    assert end_event['status'] == 'SUCCESS'
    assert end_event['duration_seconds'] is not None
    assert end_event['duration_seconds'] > 0


def test_job_tracker_metrics_tracking():
    """Test that job tracker correctly stores metrics in END event"""
    
    config = PipelineConfig()
    bq_manager = BigQueryManager(config)
    job_tracker = JobTracker(bq_manager, config)
    
    # Start job and update metrics
    job_id = job_tracker.start_job("Test_Job_Metrics", environment="testing")
    
    job_tracker.update_metrics(api_requests_made=5, sensors_processed=100)
    job_tracker.increment_metric("new_sensors_found", 3)
    
    # Verify metrics in memory
    metrics = job_tracker.get_current_metrics()
    assert metrics['api_requests_made'] == 5
    assert metrics['sensors_processed'] == 100
    assert metrics['new_sensors_found'] == 3
    
    # End job
    job_tracker.end_job(status="SUCCESS", notes="Metrics test")
    
    # Query to verify metrics were stored
    query = f"""
    SELECT api_requests_made, sensors_processed, new_sensors_found
    FROM `{config.PROJECT_ID}.{config.JOBS_DATASET_ID}.{config.JOBS_TABLE_ID}`
    WHERE job_id = '{job_id}' AND event_type = 'END'
    """
    
    result_df = bq_manager.execute_query(query)
    
    assert len(result_df) == 1
    assert result_df.iloc[0]['api_requests_made'] == 5
    assert result_df.iloc[0]['sensors_processed'] == 100
    assert result_df.iloc[0]['new_sensors_found'] == 3