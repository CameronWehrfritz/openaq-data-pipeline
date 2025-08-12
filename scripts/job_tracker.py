"""
Job Tracker Module
Handles job tracking, monitoring, and observability for pipeline executions
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError

from pipeline_config import PipelineConfig
from bigquery_manager import BigQueryManager


class JobTracker:
    """Handles job tracking and status updates with comprehensive monitoring capabilities"""
    
    def __init__(self, bq_manager: BigQueryManager, config: PipelineConfig):
        self.bq_manager = bq_manager
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Current job state
        self.job_id = None
        self.job_name = None
        self.start_time = None
        self.metrics = {}
        
        # Define job tracking schema
        self.job_schema = self._define_job_schema()
    
    def _define_job_schema(self) -> List[bigquery.SchemaField]:
        """Define the BigQuery schema for job tracking table"""
        return [
            bigquery.SchemaField("job_id", "STRING", mode="REQUIRED",
                                description="Unique identifier for this job execution"),
            bigquery.SchemaField("job_name", "STRING", mode="REQUIRED",
                                description="Name/type of the pipeline job"),
            bigquery.SchemaField("start_time", "TIMESTAMP", mode="REQUIRED",
                                description="When the job started execution"),
            bigquery.SchemaField("end_time", "TIMESTAMP", mode="NULLABLE",
                                description="When the job completed (success or failure)"),
            bigquery.SchemaField("status", "STRING", mode="REQUIRED",
                                description="Job status: RUNNING, SUCCESS, FAILED, CANCELLED"),
            bigquery.SchemaField("notes", "STRING", mode="NULLABLE",
                                description="Human-readable notes about job execution"),
            bigquery.SchemaField("error_message", "STRING", mode="NULLABLE",
                                description="Error message if job failed"),
            bigquery.SchemaField("rows_inserted", "INTEGER", mode="NULLABLE",
                                description="Number of rows inserted/updated during job"),
            bigquery.SchemaField("source_start_time", "TIMESTAMP", mode="NULLABLE",
                                description="Start time of source data being processed"),
            bigquery.SchemaField("source_end_time", "TIMESTAMP", mode="NULLABLE",
                                description="End time of source data being processed"),
            bigquery.SchemaField("duration_seconds", "FLOAT64", mode="NULLABLE",
                                description="Total job execution time in seconds"),
            bigquery.SchemaField("api_requests_made", "INTEGER", mode="NULLABLE",
                                description="Number of API requests made during job"),
            bigquery.SchemaField("sensors_processed", "INTEGER", mode="NULLABLE",
                                description="Number of sensors processed"),
            bigquery.SchemaField("new_sensors_found", "INTEGER", mode="NULLABLE",
                                description="Number of new sensors discovered"),
            bigquery.SchemaField("sensors_updated", "INTEGER", mode="NULLABLE",
                                description="Number of existing sensors updated"),
            bigquery.SchemaField("data_quality_issues", "INTEGER", mode="NULLABLE",
                                description="Number of data quality issues encountered"),
            bigquery.SchemaField("pipeline_version", "STRING", mode="NULLABLE",
                                description="Version of the pipeline code"),
            bigquery.SchemaField("environment", "STRING", mode="NULLABLE",
                                description="Environment where job ran (dev, prod, etc.)"),
        ]
    
    def ensure_job_tracking_table_exists(self) -> bool:
        """
        Create job tracking table if it doesn't exist
        
        Returns:
            bool: True if table exists or was created successfully
        """
        table_description = (
            "Job execution tracking for OpenAQ data pipeline. "
            "Records start/end times, status, metrics, and errors for all pipeline runs."
        )
        
        success = self.bq_manager.create_table(
            dataset_id=self.config.JOBS_DATASET_ID,
            table_id=self.config.JOBS_TABLE_ID,
            schema=self.job_schema,
            description=table_description,
            partition_field="start_time"  # Partition by start_time for better query performance
        )
        
        if success:
            self.logger.info("Job tracking table is ready")
        else:
            self.logger.error("Failed to ensure job tracking table exists")
        
        return success
    
    def start_job(self, job_name: str, environment: str = "production", 
                  pipeline_version: str = "1.0.0") -> str:
        """
        Start a new job and return job_id
        
        Args:
            job_name: Name of the job being executed
            environment: Environment (dev, staging, production)
            pipeline_version: Version of the pipeline code
            
        Returns:
            str: Unique job ID for this execution
        """
        # Generate unique job ID
        self.start_time = datetime.now(timezone.utc)
        timestamp_str = self.start_time.strftime('%Y%m%d_%H%M%S')
        unique_suffix = uuid.uuid4().hex[:8]
        self.job_id = f"job_{timestamp_str}_{unique_suffix}"
        self.job_name = job_name
        
        # Initialize metrics
        self.metrics = {
            "api_requests_made": 0,
            "sensors_processed": 0,
            "new_sensors_found": 0,
            "sensors_updated": 0,
            "data_quality_issues": 0
        }
        
        # Ensure job tracking table exists
        if not self.ensure_job_tracking_table_exists():
            self.logger.error("Cannot start job tracking - table creation failed")
            return self.job_id
        
        # Insert start record
        start_record = {
            "job_id": self.job_id,
            "job_name": job_name,
            "start_time": self.start_time.isoformat(),
            "status": "RUNNING",
            "notes": "Job started successfully",
            "environment": environment,
            "pipeline_version": pipeline_version,
            "error_message": None,
            "end_time": None,
            "duration_seconds": None,
            "rows_inserted": None,
            "source_start_time": None,
            "source_end_time": None,
            "api_requests_made": None,
            "sensors_processed": None,
            "new_sensors_found": None,
            "sensors_updated": None,
            "data_quality_issues": None
        }
        
        success = self.bq_manager.insert_rows(
            self.config.JOBS_DATASET_ID,
            self.config.JOBS_TABLE_ID,
            [start_record]
        )
        
        if success:
            self.logger.info(f"Job tracking started: {self.job_id}")
        else:
            self.logger.error(f"Failed to start job tracking for: {self.job_id}")
        
        return self.job_id
    
    def update_metrics(self, **kwargs) -> None:
        """
        Update job metrics during execution
        
        Args:
            **kwargs: Metric name-value pairs to update
        """
        for key, value in kwargs.items():
            if key in self.metrics:
                self.metrics[key] = value
                self.logger.debug(f"Updated metric {key}: {value}")
            else:
                self.logger.warning(f"Unknown metric: {key}")
    
    def increment_metric(self, metric_name: str, increment: int = 1) -> None:
        """
        Increment a counter metric
        
        Args:
            metric_name: Name of the metric to increment
            increment: Amount to increment by (default 1)
        """
        if metric_name in self.metrics:
            self.metrics[metric_name] += increment
            self.logger.debug(f"Incremented {metric_name} by {increment} to {self.metrics[metric_name]}")
        else:
            self.logger.warning(f"Unknown metric: {metric_name}")
    
    def end_job(self, status: str, notes: str = None, error_message: str = None, 
               rows_inserted: int = None, source_start_time: datetime = None,
               source_end_time: datetime = None) -> bool:
        """
        End job and update final status with comprehensive metrics
        
        Args:
            status: Final job status (SUCCESS, FAILED, CANCELLED)
            notes: Human-readable notes about execution
            error_message: Error message if job failed
            rows_inserted: Total rows inserted/updated
            source_start_time: Start time of source data processed
            source_end_time: End time of source data processed
            
        Returns:
            bool: True if job end was recorded successfully
        """
        if not self.job_id:
            self.logger.error("Cannot end job - no active job found")
            return False
        
        end_time = datetime.now(timezone.utc)
        duration = (end_time - self.start_time).total_seconds() if self.start_time else None
        
        # Build comprehensive update query
        update_query = f"""
        UPDATE `{self.config.PROJECT_ID}.{self.config.JOBS_DATASET_ID}.{self.config.JOBS_TABLE_ID}`
        SET 
            end_time = @end_time,
            status = @status,
            duration_seconds = @duration_seconds,
            notes = @notes,
            error_message = @error_message,
            rows_inserted = @rows_inserted,
            source_start_time = @source_start_time,
            source_end_time = @source_end_time,
            api_requests_made = @api_requests_made,
            sensors_processed = @sensors_processed,
            new_sensors_found = @new_sensors_found,
            sensors_updated = @sensors_updated,
            data_quality_issues = @data_quality_issues
        WHERE job_id = @job_id
        """
        
        # Prepare query parameters
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("end_time", "TIMESTAMP", end_time),
                bigquery.ScalarQueryParameter("status", "STRING", status),
                bigquery.ScalarQueryParameter("duration_seconds", "FLOAT64", duration),
                bigquery.ScalarQueryParameter("notes", "STRING", notes),
                bigquery.ScalarQueryParameter("error_message", "STRING", error_message),
                bigquery.ScalarQueryParameter("rows_inserted", "INTEGER", rows_inserted),
                bigquery.ScalarQueryParameter("source_start_time", "TIMESTAMP", source_start_time),
                bigquery.ScalarQueryParameter("source_end_time", "TIMESTAMP", source_end_time),
                bigquery.ScalarQueryParameter("api_requests_made", "INTEGER", self.metrics.get("api_requests_made")),
                bigquery.ScalarQueryParameter("sensors_processed", "INTEGER", self.metrics.get("sensors_processed")),
                bigquery.ScalarQueryParameter("new_sensors_found", "INTEGER", self.metrics.get("new_sensors_found")),
                bigquery.ScalarQueryParameter("sensors_updated", "INTEGER", self.metrics.get("sensors_updated")),
                bigquery.ScalarQueryParameter("data_quality_issues", "INTEGER", self.metrics.get("data_quality_issues")),
                bigquery.ScalarQueryParameter("job_id", "STRING", self.job_id),
            ]
        )
        
        try:
            query_job = self.bq_manager.client.query(update_query, job_config=job_config)
            query_job.result()  # Wait for completion
            
            # Log comprehensive job summary
            self.logger.info(f"Job {self.job_id} completed with status {status} in {duration:.2f}s")
            self.logger.info(f"Job metrics: {self.metrics}")
            
            if error_message:
                self.logger.error(f"Job error: {error_message}")
            
            return True
            
        except GoogleCloudError as e:
            self.logger.error(f"Failed to end job {self.job_id}: {e}")
            return False
    
    def get_job_history(self, limit: int = 10, status_filter: str = None) -> List[Dict]:
        """
        Get recent job execution history
        
        Args:
            limit: Maximum number of jobs to return
            status_filter: Optional status filter (SUCCESS, FAILED, etc.)
            
        Returns:
            List[Dict]: List of job records
        """
        try:
            # Build query
            where_clause = ""
            if status_filter:
                where_clause = f"WHERE status = '{status_filter}'"
            
            query = f"""
            SELECT *
            FROM `{self.config.PROJECT_ID}.{self.config.JOBS_DATASET_ID}.{self.config.JOBS_TABLE_ID}`
            {where_clause}
            ORDER BY start_time DESC
            LIMIT {limit}
            """
            
            result_df = self.bq_manager.execute_query(query)
            
            if result_df is not None and not result_df.empty:
                jobs = result_df.to_dict('records')
                self.logger.info(f"Retrieved {len(jobs)} job records")
                return jobs
            else:
                self.logger.info("No job history found")
                return []
                
        except Exception as e:
            self.logger.error(f"Error retrieving job history: {e}")
            return []
    
    def get_job_statistics(self, days_back: int = 30) -> Dict:
        """
        Get job execution statistics for monitoring and reporting
        
        Args:
            days_back: Number of days to look back for statistics
            
        Returns:
            Dict: Job statistics summary
        """
        try:
            query = f"""
            SELECT 
                COUNT(*) as total_jobs,
                COUNTIF(status = 'SUCCESS') as successful_jobs,
                COUNTIF(status = 'FAILED') as failed_jobs,
                COUNTIF(status = 'CANCELLED') as cancelled_jobs,
                AVG(duration_seconds) as avg_duration_seconds,
                MAX(duration_seconds) as max_duration_seconds,
                MIN(duration_seconds) as min_duration_seconds,
                SUM(COALESCE(rows_inserted, 0)) as total_rows_processed,
                SUM(COALESCE(api_requests_made, 0)) as total_api_requests,
                SUM(COALESCE(new_sensors_found, 0)) as total_new_sensors,
                SUM(COALESCE(sensors_updated, 0)) as total_sensors_updated,
                SUM(COALESCE(data_quality_issues, 0)) as total_data_quality_issues,
                MIN(start_time) as earliest_job,
                MAX(start_time) as latest_job
            FROM `{self.config.PROJECT_ID}.{self.config.JOBS_DATASET_ID}.{self.config.JOBS_TABLE_ID}`
            WHERE start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days_back} DAY)
            """
            
            result_df = self.bq_manager.execute_query(query)
            
            if result_df is not None and not result_df.empty:
                stats = result_df.iloc[0].to_dict()
                
                # Calculate success rate
                total = stats.get('total_jobs', 0)
                successful = stats.get('successful_jobs', 0)
                stats['success_rate'] = (successful / total * 100) if total > 0 else 0
                
                self.logger.info(f"Retrieved statistics for {total} jobs over {days_back} days")
                return stats
            else:
                return {"error": "No job statistics available"}
                
        except Exception as e:
            self.logger.error(f"Error getting job statistics: {e}")
            return {"error": str(e)}
    
    def get_current_job_id(self) -> Optional[str]:
        """Get the current job ID"""
        return self.job_id
    
    def get_current_metrics(self) -> Dict:
        """Get current job metrics"""
        return self.metrics.copy()
    
    def log_milestone(self, milestone: str, details: str = None) -> None:
        """
        Log a milestone during job execution
        
        Args:
            milestone: Name of the milestone reached
            details: Optional additional details
        """
        if details:
            self.logger.info(f"MILESTONE [{self.job_id}]: {milestone} - {details}")
        else:
            self.logger.info(f"MILESTONE [{self.job_id}]: {milestone}")


# Utility functions for job monitoring
def get_recent_failures(job_tracker: JobTracker, hours_back: int = 24) -> List[Dict]:
    """Get recent job failures for alerting"""
    try:
        query = f"""
        SELECT job_id, job_name, start_time, error_message, duration_seconds
        FROM `{job_tracker.config.PROJECT_ID}.{job_tracker.config.JOBS_DATASET_ID}.{job_tracker.config.JOBS_TABLE_ID}`
        WHERE status = 'FAILED' 
        AND start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {hours_back} HOUR)
        ORDER BY start_time DESC
        """
        
        result_df = job_tracker.bq_manager.execute_query(query)
        return result_df.to_dict('records') if result_df is not None else []
        
    except Exception as e:
        logging.getLogger(__name__).error(f"Error getting recent failures: {e}")
        return []


def get_performance_trends(job_tracker: JobTracker, days_back: int = 7) -> Dict:
    """Get performance trends for monitoring dashboards"""
    try:
        query = f"""
        SELECT 
            DATE(start_time) as job_date,
            COUNT(*) as daily_job_count,
            AVG(duration_seconds) as avg_duration,
            SUM(COALESCE(rows_inserted, 0)) as daily_rows_processed,
            COUNTIF(status = 'SUCCESS') as successful_jobs,
            COUNTIF(status = 'FAILED') as failed_jobs
        FROM `{job_tracker.config.PROJECT_ID}.{job_tracker.config.JOBS_DATASET_ID}.{job_tracker.config.JOBS_TABLE_ID}`
        WHERE start_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days_back} DAY)
        GROUP BY DATE(start_time)
        ORDER BY job_date DESC
        """
        
        result_df = job_tracker.bq_manager.execute_query(query)
        return result_df.to_dict('records') if result_df is not None else []
        
    except Exception as e:
        logging.getLogger(__name__).error(f"Error getting performance trends: {e}")
        return []


# Example usage and testing
if __name__ == "__main__":
    from pipeline_config import PipelineConfig
    from logger import PipelineLogger
    from bigquery_manager import BigQueryManager
    
    print("=== Job Tracker Test ===")
    
    # Initialize components
    config = PipelineConfig()
    logger_setup = PipelineLogger(config)
    bq_manager = BigQueryManager(config)
    job_tracker = JobTracker(bq_manager, config)
    
    print("✓ Job Tracker initialized")
    
    # Test job lifecycle
    job_id = job_tracker.start_job("Test_Job", environment="development")
    print(f"✓ Started test job: {job_id}")
    
    # Test metrics updates
    job_tracker.update_metrics(api_requests_made=5, sensors_processed=100)
    job_tracker.increment_metric("new_sensors_found", 3)
    job_tracker.increment_metric("sensors_updated", 2)
    
    print("✓ Updated job metrics")
    
    # Test milestone logging
    job_tracker.log_milestone("Data Fetching Complete", "Retrieved 100 sensors from API")
    job_tracker.log_milestone("Database Operations Complete")
    
    # End the job
    success = job_tracker.end_job(
        status="SUCCESS",
        notes="Test job completed successfully",
        rows_inserted=5
    )
    
    if success:
        print("✓ Job ended successfully")
    else:
        print("✗ Failed to end job")
    
    # Test job history retrieval
    history = job_tracker.get_job_history(limit=5)
    print(f"✓ Retrieved {len(history)} recent jobs")
    
    # Test statistics
    stats = job_tracker.get_job_statistics()
    if "error" not in stats:
        print(f"✓ Job statistics:")
        print(f"  Total jobs: {stats.get('total_jobs', 0)}")
        print(f"  Success rate: {stats.get('success_rate', 0):.1f}%")
        print(f"  Avg duration: {stats.get('avg_duration_seconds', 0):.2f}s")
    else:
        print(f"⚠ Statistics error: {stats['error']}")
    
    print("\n✓ Job Tracker test completed!")