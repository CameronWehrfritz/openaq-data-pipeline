"""
BigQuery Manager Module
Handles all BigQuery operations for the OpenAQ pipeline
"""

import os
import logging
import pandas as pd
from typing import Dict, List, Optional
from dotenv import load_dotenv
from google.cloud import bigquery
from google.cloud.exceptions import NotFound, GoogleCloudError

from pipeline_config import PipelineConfig


class BigQueryManager:
    """Handles all BigQuery operations"""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.client = self._initialize_client()
    
    def _initialize_client(self) -> bigquery.Client:
        """Initialize BigQuery client with comprehensive error handling"""
        try:
            # Load environment variables
            load_dotenv()
            credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
            
            # Validate credentials
            if not credentials_path:
                raise ValueError(
                    "GOOGLE_APPLICATION_CREDENTIALS environment variable not set. "
                    "Please set it to the path of your service account JSON file."
                )
            
            if not os.path.exists(credentials_path):
                raise FileNotFoundError(
                    f"Google Cloud credentials file not found: {credentials_path}"
                )
            
            self.logger.info(f"Using Google credentials: {credentials_path}")
            
            # Initialize client
            client = bigquery.Client(project=self.config.PROJECT_ID)
            
             # DEBUG: Check project mismatch
            print(f"DEBUG: Config project ID: {self.config.PROJECT_ID}")
            print(f"DEBUG: Actual BigQuery client project: {client.project}")
            print(f"DEBUG: Project match: {self.config.PROJECT_ID == client.project}")

            # Test the connection
            self._test_connection(client)
            
            self.logger.info(f"Successfully connected to BigQuery project: {self.config.PROJECT_ID}")
            return client
            
        except Exception as e:
            self.logger.error(f"Failed to initialize BigQuery client: {e}")
            raise
    
    def _test_connection(self, client: bigquery.Client):
        """Test the BigQuery connection"""
        try:
            # Simple query to test connection
            query = "SELECT 1 as test_connection"
            query_job = client.query(query)
            results = query_job.result()
            # Consume the results to ensure the query actually runs
            list(results)
            self.logger.debug("BigQuery connection test successful")
        except Exception as e:
            raise ConnectionError(f"BigQuery connection test failed: {e}")
    
    def ensure_dataset_exists(self, dataset_id: str) -> bool:
        """
        Create dataset if it doesn't exist
        
        Args:
            dataset_id: The dataset ID to create/check
            
        Returns:
            bool: True if dataset exists or was created successfully
        """
        dataset_ref = f"{self.config.PROJECT_ID}.{dataset_id}"
        
        try:
            # Check if dataset exists
            self.client.get_dataset(dataset_ref)
            self.logger.info(f"Dataset {dataset_id} already exists")
            return True
            
        except NotFound:
            self.logger.info(f"Creating dataset {dataset_id}")
            
            try:
                # Create dataset
                dataset = bigquery.Dataset(dataset_ref)
                
                # Set dataset properties
                dataset.location = "US"  # You can make this configurable
                dataset.description = f"OpenAQ pipeline dataset: {dataset_id}"
                
                created_dataset = self.client.create_dataset(dataset, timeout=30)
                self.logger.info(f"Dataset {dataset_id} created successfully in {created_dataset.location}")
                return True
                
            except GoogleCloudError as e:
                self.logger.error(f"Failed to create dataset {dataset_id}: {e}")
                return False
        
        except GoogleCloudError as e:
            self.logger.error(f"Error checking dataset {dataset_id}: {e}")
            return False
    
    def table_exists(self, dataset_id: str, table_id: str) -> bool:
        """Check if a table exists"""
        table_ref = f"{self.config.PROJECT_ID}.{dataset_id}.{table_id}"
        
        try:
            self.client.get_table(table_ref)
            return True
        except NotFound:
            return False
        except GoogleCloudError as e:
            self.logger.error(f"Error checking if table exists {table_ref}: {e}")
            return False
    
    def create_table(self, dataset_id: str, table_id: str, schema: List[bigquery.SchemaField], 
                     description: str = None, partition_field: str = None) -> bool:
        """
        Create a BigQuery table with the given schema
        
        Args:
            dataset_id: Dataset ID
            table_id: Table ID  
            schema: List of SchemaField objects
            description: Optional table description
            partition_field: Optional field to partition by (for time-based partitioning)
            
        Returns:
            bool: True if table was created successfully
        """
        table_ref = f"{self.config.PROJECT_ID}.{dataset_id}.{table_id}"
        
        try:
            # Ensure dataset exists first
            if not self.ensure_dataset_exists(dataset_id):
                return False
            
            # Check if table already exists
            if self.table_exists(dataset_id, table_id):
                self.logger.info(f"Table {table_ref} already exists")
                return True
            
            # Create table
            table = bigquery.Table(table_ref, schema=schema)
            
            if description:
                table.description = description
            
            # Set up partitioning if specified
            if partition_field:
                table.time_partitioning = bigquery.TimePartitioning(
                    type_=bigquery.TimePartitioningType.DAY,
                    field=partition_field
                )
            
            created_table = self.client.create_table(table, timeout=30)
            self.logger.info(f"Table {table_ref} created successfully")
            return True
            
        except GoogleCloudError as e:
            self.logger.error(f"Failed to create table {table_ref}: {e}")
            return False
    
    def load_table_to_df(self, dataset_id: str, table_id: str, 
                         query_filter: str = None, limit: int = None) -> pd.DataFrame:
        """
        Load BigQuery table to DataFrame with optional filtering
        
        Args:
            dataset_id: Dataset ID
            table_id: Table ID
            query_filter: Optional WHERE clause (without the WHERE keyword)
            limit: Optional limit on number of rows
            
        Returns:
            pandas.DataFrame: The query results
        """
        table_ref = f"{self.config.PROJECT_ID}.{dataset_id}.{table_id}"
        
        # Build query
        query_parts = [f"SELECT * FROM `{table_ref}`"]
        
        if query_filter:
            query_parts.append(f"WHERE {query_filter}")
        
        if limit:
            query_parts.append(f"LIMIT {limit}")
        
        query = " ".join(query_parts)
        
        try:
            self.logger.info(f"Loading table: {table_ref}")
            if query_filter or limit:
                self.logger.debug(f"Query: {query}")
            
            result = self.client.query(query).to_dataframe()
            self.logger.info(f"Loaded {len(result)} rows from {table_ref}")
            return result
            
        except NotFound:
            self.logger.warning(f"Table {table_ref} not found, returning empty DataFrame")
            return pd.DataFrame()
            
        except GoogleCloudError as e:
            self.logger.error(f"Failed to load table {table_ref}: {e}")
            raise
    
    def insert_rows(self, dataset_id: str, table_id: str, rows: List[Dict]) -> bool:
        """
        Insert rows into BigQuery table with comprehensive error handling
        
        Args:
            dataset_id: Dataset ID
            table_id: Table ID
            rows: List of dictionaries representing rows to insert
            
        Returns:
            bool: True if all rows were inserted successfully
        """
        if not rows:
            self.logger.warning("No rows provided for insertion")
            return True
        
        table_ref = f"{self.config.PROJECT_ID}.{dataset_id}.{table_id}"
        
        try:
            self.logger.info(f"Inserting {len(rows)} rows to {table_ref}")
            
            # Insert rows
            errors = self.client.insert_rows_json(table_ref, rows)
            
            if errors:
                self.logger.error(f"Errors inserting rows to {table_ref}:")
                for i, error in enumerate(errors):
                    self.logger.error(f"  Row {i}: {error}")
                return False
            
            self.logger.info(f"Successfully inserted {len(rows)} rows to {table_ref}")
            return True
            
        except GoogleCloudError as e:
            self.logger.error(f"Failed to insert rows to {table_ref}: {e}")
            return False
    
    def execute_query(self, query: str, job_config: bigquery.QueryJobConfig = None) -> Optional[pd.DataFrame]:
        """
        Execute a SQL query and return results as DataFrame
        
        Args:
            query: SQL query string
            job_config: Optional query job configuration
            
        Returns:
            pandas.DataFrame or None: Query results, or None if query doesn't return data
        """
        try:
            self.logger.debug(f"Executing query: {query[:100]}...")
            
            query_job = self.client.query(query, job_config=job_config)
            results = query_job.result()
            
            # Check if query returns data
            if query_job.job_type == 'query' and results.total_rows > 0:
                df = results.to_dataframe()
                self.logger.info(f"Query returned {len(df)} rows")
                return df
            else:
                self.logger.info("Query executed successfully (no data returned)")
                return None
                
        except GoogleCloudError as e:
            self.logger.error(f"Query execution failed: {e}")
            self.logger.debug(f"Failed query: {query}")
            raise
    
    def get_table_info(self, dataset_id: str, table_id: str) -> Optional[Dict]:
        """
        Get information about a table
        
        Returns:
            dict: Table information including schema, row count, etc.
        """
        table_ref = f"{self.config.PROJECT_ID}.{dataset_id}.{table_id}"
        
        try:
            table = self.client.get_table(table_ref)
            
            info = {
                "table_id": table.table_id,
                "dataset_id": table.dataset_id,
                "project_id": table.project,
                "created": table.created.isoformat() if table.created else None,
                "modified": table.modified.isoformat() if table.modified else None,
                "num_rows": table.num_rows,
                "num_bytes": table.num_bytes,
                "schema": [{"name": field.name, "type": field.field_type, "mode": field.mode} 
                          for field in table.schema],
                "description": table.description
            }
            
            return info
            
        except NotFound:
            self.logger.warning(f"Table {table_ref} not found")
            return None
        except GoogleCloudError as e:
            self.logger.error(f"Error getting table info for {table_ref}: {e}")
            return None
    
    def delete_table(self, dataset_id: str, table_id: str) -> bool:
        """Delete a table (use with caution!)"""
        table_ref = f"{self.config.PROJECT_ID}.{dataset_id}.{table_id}"
        
        try:
            self.client.delete_table(table_ref, not_found_ok=True)
            self.logger.info(f"Table {table_ref} deleted successfully")
            return True
        except GoogleCloudError as e:
            self.logger.error(f"Failed to delete table {table_ref}: {e}")
            return False


# Utility functions
def create_schema_field(name: str, field_type: str, mode: str = "NULLABLE", 
                       description: str = None) -> bigquery.SchemaField:
    """Helper function to create BigQuery schema fields"""
    return bigquery.SchemaField(
        name=name,
        field_type=field_type,
        mode=mode,
        description=description
    )


# Example usage and testing
if __name__ == "__main__":
    from pipeline_config import PipelineConfig
    
    # Test the BigQuery manager
    config = PipelineConfig()
    bq_manager = BigQueryManager(config)
    
    print("BigQuery Manager initialized successfully!")
    
    # Test dataset creation
    test_dataset = "test_dataset"
    if bq_manager.ensure_dataset_exists(test_dataset):
        print(f"Dataset {test_dataset} is ready")
    
    # Test table info
    info = bq_manager.get_table_info(config.DATASET_ID, config.SENSOR_TABLE_ID)
    if info:
        print(f"Sensor table has {info['num_rows']} rows")
    else:
        print("Sensor table not found or error occurred")