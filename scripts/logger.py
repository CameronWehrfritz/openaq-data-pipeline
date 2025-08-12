"""
Pipeline Logger Module
Handles logging configuration and operations for the OpenAQ pipeline
"""

import os
import logging
import warnings
from datetime import datetime
from pipeline_config import PipelineConfig


class PipelineLogger:
    """Handles logging configuration and operations"""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.logger = self.setup_logging()
    
    def setup_logging(self) -> logging.Logger:
        """Configure logging with both file and console handlers"""
        # Create logs directory if it doesn't exist
        os.makedirs(self.config.LOGS_DIR, exist_ok=True)
        
        # Generate log filename with current date
        log_filename = os.path.join(
            self.config.LOGS_DIR, 
            f"pipeline_{datetime.now().strftime('%Y%m%d')}.log"
        )
        
        # Get root logger and clear any existing handlers (prevents duplicates in Jupyter)
        logger = logging.getLogger()
        logger.handlers.clear()  # This prevents the duplicate log messages!
        
        # Create formatter for consistent log format
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        
        # Setup file handler for persistent logging
        file_handler = logging.FileHandler(log_filename, mode='a', encoding='utf-8')
        file_handler.setFormatter(formatter)
        file_handler.setLevel(getattr(logging, self.config.LOG_LEVEL))
        
        # Setup console handler for real-time output
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)  # Always show INFO+ on console
        
        # Configure root logger
        logger.setLevel(getattr(logging, self.config.LOG_LEVEL))
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        # Suppress common warnings that aren't actionable
        self._suppress_common_warnings()
        
        # Log the logging setup
        logger.info(f"Logging initialized - File: {log_filename}, Level: {self.config.LOG_LEVEL}")
        
        return logger
    
    def _suppress_common_warnings(self):
        """Suppress common warnings that aren't actionable in our pipeline"""
        
        # Suppress BigQuery Storage API warning if user hasn't installed the optional dependency
        warnings.filterwarnings(
            "ignore", 
            message="BigQuery Storage module not found",
            category=UserWarning
        )
        
        # Suppress pandas performance warnings for small datasets
        warnings.filterwarnings(
            "ignore",
            message=".*pandas.*performance.*",
            category=UserWarning
        )
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger with a specific name (useful for different modules)"""
        return logging.getLogger(name)
    
    def set_level(self, level: str):
        """Dynamically change logging level"""
        numeric_level = getattr(logging, level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError(f'Invalid log level: {level}')
        
        # Update all handlers
        root_logger = logging.getLogger()
        root_logger.setLevel(numeric_level)
        
        for handler in root_logger.handlers:
            if isinstance(handler, logging.FileHandler):
                handler.setLevel(numeric_level)
        
        logging.info(f"Logging level changed to {level.upper()}")
    
    def log_pipeline_start(self, pipeline_name: str, job_id: str):
        """Log pipeline start with consistent formatting"""
        logger = logging.getLogger(__name__)
        logger.info("=" * 60)
        logger.info(f"STARTING: {pipeline_name}")
        logger.info(f"JOB ID: {job_id}")
        logger.info(f"TIMESTAMP: {datetime.now().isoformat()}")
        logger.info("=" * 60)
    
    def log_pipeline_end(self, pipeline_name: str, job_id: str, success: bool, duration: float = None):
        """Log pipeline end with consistent formatting"""
        logger = logging.getLogger(__name__)
        status = "SUCCESS" if success else "FAILED"
        
        logger.info("=" * 60)
        logger.info(f"COMPLETED: {pipeline_name} - {status}")
        logger.info(f"JOB ID: {job_id}")
        if duration:
            logger.info(f"DURATION: {duration:.2f} seconds")
        logger.info(f"TIMESTAMP: {datetime.now().isoformat()}")
        logger.info("=" * 60)
    
    def log_metrics(self, metrics: dict):
        """Log pipeline metrics in a structured way"""
        logger = logging.getLogger(__name__)
        logger.info("PIPELINE METRICS:")
        for key, value in metrics.items():
            logger.info(f"  • {key}: {value}")


# Utility functions for easy logging setup
def setup_logger(config: PipelineConfig) -> PipelineLogger:
    """Convenience function to set up logging"""
    return PipelineLogger(config)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger (assumes logging is already configured)"""
    return logging.getLogger(name)


# Example usage and testing
if __name__ == "__main__":
    # Test the logger setup
    from pipeline_config import PipelineConfig
    
    config = PipelineConfig()
    pipeline_logger = PipelineLogger(config)
    
    # Test different log levels
    test_logger = logging.getLogger("test")
    test_logger.debug("This is a debug message")
    test_logger.info("This is an info message")
    test_logger.warning("This is a warning message")
    test_logger.error("This is an error message")
    
    # Test pipeline logging methods
    pipeline_logger.log_pipeline_start("Test Pipeline", "test_job_123")
    
    # Test metrics logging
    metrics = {
        "sensors_processed": 59,
        "new_sensors": 0,
        "updated_sensors": 0,
        "api_calls_made": 3,
        "execution_time_seconds": 45.2
    }
    pipeline_logger.log_metrics(metrics)
    
    pipeline_logger.log_pipeline_end("Test Pipeline", "test_job_123", True, 45.2)
    
    print("Logger test completed! Check the logs directory.")