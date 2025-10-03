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
    """Handles job tracking with INSERT-based event recording (avoids streaming buffer issues)"""
    
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
        """Define the BigQuery schema for job tracking table with event-based structure"""
        return [
            bigquery.SchemaField("job_id", "STRING", mode="REQUIRED",
                                description="Unique identifier for this job execution"),
            bigquery.SchemaField("event_type", "STRING", mode="REQUIRED",
                                description="Event type: START or END"),
            bigquery.SchemaField("event_time", "TIMESTAMP", mode="REQUIRED",
                                description="When this event occurred"),
            bigquery.SchemaField("job_name", "STRING", mode="REQUIRED",
                                description="Name/type of the pipeline job"),
            bigquery.SchemaField("status", "STRING", mode="REQUIRED",
                                description="Job status: RUNNING (for START), SUCCESS/FAILED/CANCELLED (for END)"),
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
                                description="Total job execution time in seconds (END events only)"),
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
            "Uses event-based recording: each job has START and END events. "
            "Avoids BigQuery streaming buffer UPDATE limitations."
        )
        
        success = self.bq_manager.create_table(
            dataset_id=self.config.JOBS_DATASET_ID,
            table_id=self.config.JOBS_TABLE_ID,
            schema=self.job_schema,
            description=table_description,
            partition_field="event_time"  # Partition by event_time for better query performance
        )
        
        if success:
            self.logger.info("Job tracking table is ready")
        else:
            self.logger.error("Failed to ensure job tracking table exists")
        
        return success
    
    def start_job(self, job_name: str, environment: str = "production", 
                  pipeline_version: str = "1.0.0") -> str:
        """
        Start a new job by inserting a START event
        
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
        
        # Insert START event
        start_event = {
            "job_id": self.job_id,
            "event_type": "START",
            "event_time": self.start_time.isoformat(),
            "job_name": job_name,
            "status": "RUNNING",
            "notes": "Job started successfully",
            "environment": environment,
            "pipeline_version": pipeline_version,
            "error_message": None,
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
            [start_event]
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
        End job by inserting an END event (no UPDATE - avoids streaming buffer issues)
        
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
        
        # Insert END event
        end_event = {
            "job_id": self.job_id,
            "event_type": "END",
            "event_time": end_time.isoformat(),
            "job_name": self.job_name,
            "status": status,
            "notes": notes,
            "error_message": error_message,
            "rows_inserted": rows_inserted,
            "source_start_time": source_start_time.isoformat() if source_start_time else None,
            "source_end_time": source_end_time.isoformat() if source_end_time else None,
            "duration_seconds": duration,
            "api_requests_made": self.metrics.get("api_requests_made"),
            "sensors_processed": self.metrics.get("sensors_processed"),
            "new_sensors_found": self.metrics.get("new_sensors_found"),
            "sensors_updated": self.metrics.get("sensors_updated"),
            "data_quality_issues": self.metrics.get("data_quality_issues"),
            "environment": None,  # Only recorded at START
            "pipeline_version": None  # Only recorded at START
        }
        
        success = self.bq_manager.insert_rows(
            self.config.JOBS_DATASET_ID,
            self.config.JOBS_TABLE_ID,
            [end_event]
        )
        
        if success:
            self.logger.info(f"Job {self.job_id} completed with status {status} in {duration:.2f}s")
            self.logger.info(f"Job metrics: {self.metrics}")
            if error_message:
                self.logger.error(f"Job error: {error_message}")
        else:
            self.logger.error(f"Failed to record end event for job {self.job_id}")
        
        return success
    
    def get_job_history(self, limit: int = 10, status_filter: str = None) -> List[Dict]:
        """
        Get recent job execution history by joining START and END events
        
        Args:
            limit: Maximum number of jobs to return
            status_filter: Optional status filter (SUCCESS, FAILED, etc.)
            
        Returns:
            List[Dict]: List of complete job records
        """
        try:
            # Build query that joins START and END events
            where_clause = ""
            if status_filter:
                where_clause = f"WHERE e.status = '{status_filter}'"
            
            query = f"""
            SELECT 
                s.job_id,
                s.job_name,
                s.event_time as start_time,
                e.event_time as end_time,
                e.status,
                e.duration_seconds,
                e.notes,
                e.error_message,
                e.rows_inserted,
                e.api_requests_made,
                e.sensors_processed,
                e.new_sensors_found,
                e.sensors_updated,
                s.environment,
                s.pipeline_version
            FROM `{self.config.PROJECT_ID}.{self.config.JOBS_DATASET_ID}.{self.config.JOBS_TABLE_ID}` s
            LEFT JOIN `{self.config.PROJECT_ID}.{self.config.JOBS_DATASET_ID}.{self.config.JOBS_TABLE_ID}` e
                ON s.job_id = e.job_id AND e.event_type = 'END'
            WHERE s.event_type = 'START'
            {where_clause}
            ORDER BY s.event_time DESC
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
        Get job execution statistics using END events only
        
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
                MIN(event_time) as earliest_job,
                MAX(event_time) as latest_job
            FROM `{self.config.PROJECT_ID}.{self.config.JOBS_DATASET_ID}.{self.config.JOBS_TABLE_ID}`
            WHERE event_type = 'END'
            AND event_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days_back} DAY)
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
    """Get recent job failures for alerting (queries END events only)"""
    try:
        query = f"""
        SELECT job_id, job_name, event_time as end_time, error_message, duration_seconds
        FROM `{job_tracker.config.PROJECT_ID}.{job_tracker.config.JOBS_DATASET_ID}.{job_tracker.config.JOBS_TABLE_ID}`
        WHERE event_type = 'END'
        AND status = 'FAILED' 
        AND event_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {hours_back} HOUR)
        ORDER BY event_time DESC
        """
        
        result_df = job_tracker.bq_manager.execute_query(query)
        return result_df.to_dict('records') if result_df is not None else []
        
    except Exception as e:
        logging.getLogger(__name__).error(f"Error getting recent failures: {e}")
        return []


def get_performance_trends(job_tracker: JobTracker, days_back: int = 7) -> Dict:
    """Get performance trends for monitoring dashboards (queries END events only)"""
    try:
        query = f"""
        SELECT 
            DATE(event_time) as job_date,
            COUNT(*) as daily_job_count,
            AVG(duration_seconds) as avg_duration,
            SUM(COALESCE(rows_inserted, 0)) as daily_rows_processed,
            COUNTIF(status = 'SUCCESS') as successful_jobs,
            COUNTIF(status = 'FAILED') as failed_jobs
        FROM `{job_tracker.config.PROJECT_ID}.{job_tracker.config.JOBS_DATASET_ID}.{job_tracker.config.JOBS_TABLE_ID}`
        WHERE event_type = 'END'
        AND event_time >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL {days_back} DAY)
        GROUP BY DATE(event_time)
        ORDER BY job_date DESC
        """
        
        result_df = job_tracker.bq_manager.execute_query(query)
        return result_df.to_dict('records') if result_df is not None else []
        
    except Exception as e:
        logging.getLogger(__name__).error(f"Error getting performance trends: {e}")
        return []