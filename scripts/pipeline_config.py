"""
Pipeline Configuration Module
Contains all configuration constants and settings for the OpenAQ pipeline
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class PipelineConfig:
    """Configuration class for the OpenAQ pipeline"""
    
    # OpenAQ API Configuration
    OPENAQ_API_KEY = os.getenv('OPENAQ_API_KEY')
    OPENAQ_API_BASE: str = "https://api.openaq.org/v3"
    API_REQUEST_LIMIT: int = 1000
    API_TIMEOUT: int = 30
    MAX_RETRIES: int = 3
    RETRY_DELAY: int = 1

    # Geographic Boundaries - California bounding box coordinates
    CA_LAT_MIN: float = 32.5
    CA_LAT_MAX: float = 42.0
    CA_LON_MIN: float = -124.5
    CA_LON_MAX: float = -114.0
    
    # BigQuery Configuration
    PROJECT_ID: str = field(default_factory=lambda: os.getenv('PROJECT_ID', ''))
    PROJECT_ID: str = "openaq-data-pipeline-468404"
    DATASET_ID: str = "openaq_ca"
    JOBS_DATASET_ID: str = "openaq_jobs"
    
    # Table Names
    SENSOR_TABLE_ID: str = "pm25_ca_sensors"
    HOURLY_TABLE_ID: str = "pm25_ca_hourly"
    JOBS_TABLE_ID: str = "job_tracking"
    
    # Logging Configuration
    LOGS_DIR: str = "logs"
    LOG_LEVEL: str = "INFO"
    
    # Performance Settings
    BATCH_SIZE: int = 1000  # For future batch processing
    
    @property
    def full_sensor_table_id(self) -> str:
        """Return fully qualified sensor table ID"""
        return f"{self.PROJECT_ID}.{self.DATASET_ID}.{self.SENSOR_TABLE_ID}"
    
    @property
    def full_hourly_table_id(self) -> str:
        """Return fully qualified hourly table ID"""
        return f"{self.PROJECT_ID}.{self.DATASET_ID}.{self.HOURLY_TABLE_ID}"
    
    @property
    def full_jobs_table_id(self) -> str:
        """Return fully qualified jobs table ID"""
        return f"{self.PROJECT_ID}.{self.JOBS_DATASET_ID}.{self.JOBS_TABLE_ID}"
    
    def validate(self) -> bool:
        """Validate configuration settings"""
        if not self.PROJECT_ID:
            raise ValueError("PROJECT_ID cannot be empty")
        
        if self.API_REQUEST_LIMIT <= 0:
            raise ValueError("API_REQUEST_LIMIT must be positive")
        
        if self.CA_LAT_MIN >= self.CA_LAT_MAX:
            raise ValueError("Invalid latitude bounds")
        
        if self.CA_LON_MIN >= self.CA_LON_MAX:
            raise ValueError("Invalid longitude bounds")
        
        return True


# specialized configs for different environments
@dataclass
class DevelopmentConfig(PipelineConfig):
    """Development environment configuration"""
    API_REQUEST_LIMIT: int = 100  # Smaller limits for testing
    LOG_LEVEL: str = "DEBUG"
    PROJECT_ID: str = "openaq-data-pipeline-dev"

@dataclass
class TestingConfig(PipelineConfig):
    """Testing environment configuration"""
    API_REQUEST_LIMIT: int = 500  # Between dev and prod
    LOG_LEVEL: str = "INFO"
    PROJECT_ID: str = "openaq-data-pipeline-test"
    MAX_RETRIES: int = 3
    # Might use test datasets or sanitized production data

@dataclass
class ProductionConfig(PipelineConfig):
    """Production environment configuration"""
    API_REQUEST_LIMIT: int = 1000
    LOG_LEVEL: str = "INFO"
    MAX_RETRIES: int = 5  # More retries in production
    

def get_config(environment: str = "production") -> PipelineConfig:
    """Factory function to get appropriate config based on environment"""
    if environment.lower() == "development":
        return DevelopmentConfig()
    elif environment.lower() == "testing":
        return TestingConfig()
    elif environment.lower() == "production":
        return ProductionConfig()
    else:
        return PipelineConfig()