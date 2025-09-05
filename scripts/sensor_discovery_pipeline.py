#!/usr/bin/env python3
"""
OpenAQ Sensor Discovery Pipeline
Main execution script for automated sensor discovery and registration

Usage:
    python sensor_discovery_pipeline.py

Environment Variables Required:
    - OPENAQ_API_KEY: OpenAQ API key
    - GOOGLE_APPLICATION_CREDENTIALS: Path to Google Cloud service account JSON

Author: Cameron Wehrfritz
Date: 2025-08-11
"""

from dotenv import load_dotenv
load_dotenv()

import os
import sys
import logging
from typing import Dict

# Import pipeline components
from pipeline_config import PipelineConfig, get_config
from logger import PipelineLogger
from bigquery_manager import BigQueryManager
from openaq_client import OpenAQClient
from sensor_manager import SensorManager
from job_tracker import JobTracker


def main() -> int:
    """
    Main pipeline execution function
    
    Returns:
        int: Exit code (0 for success, 1 for failure)
    """
    exit_code = 0
    logger = None
    job_tracker = None
    
    try:
        # Initialize configuration based on environment
        environment = os.getenv('ENVIRONMENT', 'production')
        config = get_config(environment)
        config.validate()
        
        # Setup logging
        logger_setup = PipelineLogger(config)
        logger = logging.getLogger(__name__)
        
        # Initialize managers
        bq_manager = BigQueryManager(config)
        openaq_client = OpenAQClient(config)
        sensor_manager = SensorManager(bq_manager, config)
        job_tracker = JobTracker(bq_manager, config)
        
        # Start job tracking
        job_id = job_tracker.start_job("OpenAQ_PM25_Sensor_Discovery")
        logger.info(f"Started job: {job_id}")
        
        logger.info("=" * 60)
        logger.info("Starting OpenAQ PM2.5 Sensor Discovery Pipeline")
        logger.info("=" * 60)
        
        # Fetch sensor data from OpenAQ
        logger.info("Fetching PM2.5 sensor data from OpenAQ API...")
        sensors_df = openaq_client.fetch_pm25_ca_sensors()
        
        if sensors_df.empty:
            raise ValueError("No sensors found - this seems unusual")
        
        logger.info(f"Successfully fetched {len(sensors_df)} sensors from OpenAQ")
        
        # Process sensor updates (new/existing comparison and database operations)
        logger.info("Processing sensor updates...")
        update_results = sensor_manager.process_sensor_updates(sensors_df)
        
        if not update_results["success"]:
            raise ValueError("Failed to process all sensor updates")
        
        # Log results
        logger.info("Sensor processing completed:")
        logger.info(f"  • New sensors added: {update_results['new_sensors']}")
        logger.info(f"  • Existing sensors updated: {update_results['updated_sensors']}")
        logger.info(f"  • Total sensors processed: {update_results['total_processed']}")
        
        # End job successfully
        job_tracker.end_job(
            status="SUCCESS",
            notes=f"Successfully processed {update_results['total_processed']} sensors "
                 f"({update_results['new_sensors']} new, {update_results['updated_sensors']} updated)",
            rows_inserted=update_results['total_processed']
        )
        
        logger.info("Pipeline completed successfully!")
        
    except KeyboardInterrupt:
        logger.info("Pipeline interrupted by user")
        if job_tracker:
            job_tracker.end_job(
                status="CANCELLED",
                notes="Pipeline was cancelled by user"
            )
        exit_code = 130  # Standard exit code for SIGINT
        
    except Exception as e:
        if logger:
            logger.error(f"Pipeline failed with error: {e}", exc_info=True)
        else:
            print(f"Pipeline failed during initialization: {e}")
            
        if job_tracker:
            job_tracker.end_job(
                status="FAILED",
                error_message=str(e),
                notes="Pipeline execution failed"
            )
        exit_code = 1
    
    return exit_code


def validate_environment():
    """Validate required environment variables are present"""
    import os
    
    required_vars = [
        "OPENAQ_API_KEY",
        "GOOGLE_APPLICATION_CREDENTIALS"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"Error: Missing required environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file or environment setup.")
        return False
    
    return True


if __name__ == "__main__":
    # Validate environment before running
    if not validate_environment():
        sys.exit(1)
    
    # Run pipeline
    exit_code = main()
    sys.exit(exit_code)