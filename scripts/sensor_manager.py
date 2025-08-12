"""
Sensor Manager Module
Handles sensor data comparison, validation, and database operations
"""

import logging
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from google.cloud import bigquery
from google.cloud.exceptions import NotFound, GoogleCloudError

from pipeline_config import PipelineConfig
from bigquery_manager import BigQueryManager


class SensorManager:
    """Manages sensor data comparison and updates with comprehensive business logic"""
    
    def __init__(self, bq_manager: BigQueryManager, config: PipelineConfig):
        self.bq_manager = bq_manager
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Define table schema for sensors
        self.sensor_schema = self._define_sensor_schema()
    
    def _define_sensor_schema(self) -> List[bigquery.SchemaField]:
        """Define the BigQuery schema for the sensor table"""
        return [
            bigquery.SchemaField("sensor_id", "STRING", mode="REQUIRED", 
                                description="Unique sensor identifier from OpenAQ"),
            bigquery.SchemaField("location_id", "STRING", mode="REQUIRED",
                                description="Location identifier from OpenAQ"),
            bigquery.SchemaField("location_name", "STRING", mode="NULLABLE",
                                description="Human-readable location name"),
            bigquery.SchemaField("locality", "STRING", mode="NULLABLE",
                                description="City or locality name"),
            bigquery.SchemaField("timezone", "STRING", mode="NULLABLE",
                                description="Timezone identifier"),
            bigquery.SchemaField("country_id", "STRING", mode="NULLABLE",
                                description="Country identifier"),
            bigquery.SchemaField("country_code", "STRING", mode="NULLABLE",
                                description="ISO country code"),
            bigquery.SchemaField("country_name", "STRING", mode="NULLABLE",
                                description="Country name"),
            bigquery.SchemaField("owner_id", "STRING", mode="NULLABLE",
                                description="Data owner identifier"),
            bigquery.SchemaField("owner_name", "STRING", mode="NULLABLE",
                                description="Data owner name"),
            bigquery.SchemaField("provider_id", "STRING", mode="NULLABLE",
                                description="Data provider identifier"),
            bigquery.SchemaField("provider_name", "STRING", mode="NULLABLE",
                                description="Data provider name"),
            bigquery.SchemaField("is_mobile", "BOOLEAN", mode="NULLABLE",
                                description="Whether the sensor is mobile"),
            bigquery.SchemaField("is_monitor", "BOOLEAN", mode="NULLABLE",
                                description="Whether this is a reference monitor"),
            bigquery.SchemaField("lat", "FLOAT64", mode="REQUIRED",
                                description="Latitude coordinate"),
            bigquery.SchemaField("lon", "FLOAT64", mode="REQUIRED",
                                description="Longitude coordinate"),
            bigquery.SchemaField("datetimeFirst", "TIMESTAMP", mode="NULLABLE",
                                description="First measurement timestamp from OpenAQ"),
            bigquery.SchemaField("datetimeLast", "TIMESTAMP", mode="NULLABLE",
                                description="Last measurement timestamp from OpenAQ"),
            bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED",
                                description="When this record was created in our system"),
            bigquery.SchemaField("updated_at", "TIMESTAMP", mode="REQUIRED",
                                description="When this record was last updated"),
        ]
    
    def ensure_sensors_table_exists(self) -> bool:
        """
        Create sensors table if it doesn't exist
        
        Returns:
            bool: True if table exists or was created successfully
        """
        table_description = (
            "PM2.5 sensor metadata for California. Contains sensor locations, "
            "ownership information, and operational status from OpenAQ API."
        )
        
        # Check if table already exists with correct schema
        if self.bq_manager.table_exists(self.config.DATASET_ID, self.config.SENSOR_TABLE_ID):
            self.logger.info("Sensors table already exists - checking schema compatibility")
            
            # Get existing table info
            table_info = self.bq_manager.get_table_info(self.config.DATASET_ID, self.config.SENSOR_TABLE_ID)
            
            if table_info:
                existing_fields = {field['name'] for field in table_info['schema']}
                required_fields = {field.name for field in self.sensor_schema}
                
                missing_fields = required_fields - existing_fields
                if missing_fields:
                    self.logger.warning(f"Table exists but missing fields: {missing_fields}")
                    self.logger.info("Consider recreating table with updated schema")
                else:
                    self.logger.info("Table schema is compatible")
                    return True
        
        # Create or recreate table
        success = self.bq_manager.create_table(
            dataset_id=self.config.DATASET_ID,
            table_id=self.config.SENSOR_TABLE_ID,
            schema=self.sensor_schema,
            description=table_description
        )
        
        if success:
            self.logger.info("Sensors table is ready")
        else:
            self.logger.error("Failed to ensure sensors table exists")
        
        return success
    
    def get_existing_sensors(self) -> pd.DataFrame:
        """
        Load existing sensors from BigQuery
        
        Returns:
            pandas.DataFrame: Existing sensors, or empty DataFrame if none found
        """
        try:
            if not self.bq_manager.table_exists(self.config.DATASET_ID, self.config.SENSOR_TABLE_ID):
                self.logger.info("Sensors table doesn't exist - no existing sensors to load")
                return pd.DataFrame()
            
            existing_sensors = self.bq_manager.load_table_to_df(
                self.config.DATASET_ID, 
                self.config.SENSOR_TABLE_ID
            )
            
            self.logger.info(f"Loaded {len(existing_sensors)} existing sensors from BigQuery")
            return existing_sensors
            
        except Exception as e:
            self.logger.warning(f"Could not load existing sensors: {e}")
            return pd.DataFrame()
    
    def compare_sensors(self, fetched_sensors: pd.DataFrame, 
                       existing_sensors: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Compare fetched sensors with existing ones to identify new and updated sensors
        
        Args:
            fetched_sensors: DataFrame of sensors from OpenAQ API
            existing_sensors: DataFrame of sensors from BigQuery
            
        Returns:
            Tuple[pd.DataFrame, pd.DataFrame]: (new_sensors_df, updated_sensors_df)
        """
        if existing_sensors.empty:
            self.logger.info("No existing sensors found - all fetched sensors are new")
            return fetched_sensors.copy(), pd.DataFrame()
        
        if fetched_sensors.empty:
            self.logger.warning("No fetched sensors provided for comparison")
            return pd.DataFrame(), pd.DataFrame()
        
        # Get sensor ID sets for comparison
        existing_sensor_ids = set(existing_sensors['sensor_id'].tolist())
        fetched_sensor_ids = set(fetched_sensors['sensor_id'].tolist())
        
        # Identify new sensors (in fetched but not in existing)
        new_sensor_ids = fetched_sensor_ids - existing_sensor_ids
        
        # Identify potentially updated sensors (in both datasets)
        potentially_updated_ids = fetched_sensor_ids & existing_sensor_ids
        
        self.logger.debug(f"Sensor comparison: {len(new_sensor_ids)} potentially new, "
                         f"{len(potentially_updated_ids)} potentially updated")
        
        # Extract new sensors
        new_sensors = fetched_sensors[fetched_sensors['sensor_id'].isin(new_sensor_ids)].copy()
        
        # Check for actual updates in existing sensors
        updated_sensors_list = []
        
        if potentially_updated_ids:
            for sensor_id in potentially_updated_ids:
                try:
                    fetched_row = fetched_sensors[fetched_sensors['sensor_id'] == sensor_id].iloc[0]
                    existing_row = existing_sensors[existing_sensors['sensor_id'] == sensor_id].iloc[0]
                    
                    if self._sensor_needs_update(fetched_row, existing_row):
                        updated_sensors_list.append(fetched_row.to_dict())
                        
                except (IndexError, KeyError) as e:
                    self.logger.warning(f"Error comparing sensor {sensor_id}: {e}")
                    continue
        
        # Create DataFrame from updated sensors list
        updated_sensors_df = pd.DataFrame(updated_sensors_list) if updated_sensors_list else pd.DataFrame()
        
        self.logger.info(f"Sensor comparison complete: {len(new_sensors)} new, {len(updated_sensors_df)} updated")
        
        return new_sensors, updated_sensors_df
    
    def _sensor_needs_update(self, fetched_row: pd.Series, existing_row: pd.Series) -> bool:
        """
        Determine if a sensor needs updating based on comparison of fetched vs existing data
        
        Args:
            fetched_row: Sensor data from OpenAQ API
            existing_row: Sensor data from BigQuery
            
        Returns:
            bool: True if sensor needs updating
        """
        sensor_id = fetched_row.get('sensor_id', 'unknown')
        
        # Compare datetimeLast to see if sensor has newer data
        try:
            fetched_last = self._parse_timestamp(fetched_row.get('datetimeLast'))
            existing_last = self._parse_timestamp(existing_row.get('datetimeLast'))
            
            if fetched_last and existing_last:
                if fetched_last > existing_last:
                    self.logger.debug(f"Sensor {sensor_id} has newer data: {fetched_last} > {existing_last}")
                    return True
            elif fetched_last and not existing_last:
                self.logger.debug(f"Sensor {sensor_id} now has timestamp data")
                return True
                
        except Exception as e:
            self.logger.warning(f"Error comparing timestamps for sensor {sensor_id}: {e}")
        
        # Check for changes in other important fields
        fields_to_check = ['location_name', 'locality', 'is_mobile', 'is_monitor', 'lat', 'lon']
        
        for field in fields_to_check:
            fetched_val = fetched_row.get(field)
            existing_val = existing_row.get(field)
            
            # Handle coordinate changes with tolerance for floating point precision
            if field in ['lat', 'lon']:
                if self._coordinates_changed(fetched_val, existing_val):
                    self.logger.debug(f"Sensor {sensor_id} coordinates changed: {field} {existing_val} -> {fetched_val}")
                    return True
            else:
                if fetched_val != existing_val:
                    self.logger.debug(f"Sensor {sensor_id} field changed: {field} '{existing_val}' -> '{fetched_val}'")
                    return True
        
        return False
    
    def _parse_timestamp(self, timestamp_str: Optional[str]) -> Optional[datetime]:
        """Safely parse timestamp string or dict to datetime object"""
        if not timestamp_str or pd.isna(timestamp_str):
            return None
        
        try:
            # Handle OpenAQ timestamp dictionary format
            if isinstance(timestamp_str, dict):
                utc_timestamp = timestamp_str.get('utc')
                if utc_timestamp:
                    return pd.to_datetime(utc_timestamp, utc=True)
                else:
                    return None
            
            # Handle string timestamps
            elif isinstance(timestamp_str, str):
                return pd.to_datetime(timestamp_str, utc=True)
            
            # Already a datetime
            elif isinstance(timestamp_str, datetime):
                return timestamp_str
            
            else:
                return None
                
        except (ValueError, TypeError) as e:
            self.logger.warning(f"Could not parse timestamp '{timestamp_str}': {e}")
            return None
    
    def _coordinates_changed(self, new_val: float, old_val: float, tolerance: float = 0.0001) -> bool:
        """Check if coordinates changed beyond tolerance (accounts for floating point precision)"""
        if new_val is None or old_val is None:
            return new_val != old_val
        
        try:
            return abs(float(new_val) - float(old_val)) > tolerance
        except (ValueError, TypeError):
            return new_val != old_val
    
    def prepare_sensors_for_insert(self, sensors_df: pd.DataFrame, is_update: bool = False) -> List[Dict]:
        """
        Prepare sensor data for BigQuery insertion with proper timestamps and validation
        
        Args:
            sensors_df: DataFrame containing sensor data
            is_update: Whether this is an update operation (affects created_at field)
            
        Returns:
            List[Dict]: List of dictionaries ready for BigQuery insertion
        """
        if sensors_df.empty:
            return []
        
        current_time = datetime.now(timezone.utc)
        rows = []
        
        for _, row in sensors_df.iterrows():
            # Convert pandas timestamps to ISO strings for BigQuery
            datetime_first = self._format_timestamp_for_bq(row.get('datetimeFirst'))
            datetime_last = self._format_timestamp_for_bq(row.get('datetimeLast'))
            
            sensor_row = {
                "sensor_id": row.get('sensor_id'),
                "location_id": row.get('location_id'),
                "location_name": row.get('location_name'),
                "locality": row.get('locality'),
                "timezone": row.get('timezone'),
                "country_id": row.get('country_id'),
                "country_code": row.get('country_code'),
                "country_name": row.get('country_name'),
                "owner_id": row.get('owner_id'),
                "owner_name": row.get('owner_name'),
                "provider_id": row.get('provider_id'),
                "provider_name": row.get('provider_name'),
                "is_mobile": row.get('is_mobile'),
                "is_monitor": row.get('is_monitor'),
                "lat": float(row.get('lat')) if row.get('lat') is not None else None,
                "lon": float(row.get('lon')) if row.get('lon') is not None else None,
                "datetimeFirst": datetime_first,
                "datetimeLast": datetime_last,
                "created_at": current_time.isoformat() if not is_update else None,
                "updated_at": current_time.isoformat()
            }
            
            # Remove None values for created_at in updates
            if is_update and sensor_row["created_at"] is None:
                del sensor_row["created_at"]
            
            rows.append(sensor_row)
        
        self.logger.debug(f"Prepared {len(rows)} sensor records for {'update' if is_update else 'insert'}")
        return rows
    
    def _format_timestamp_for_bq(self, timestamp_value) -> Optional[str]:
        """Format timestamp for BigQuery insertion - handles OpenAQ timestamp format"""
        if timestamp_value is None or pd.isna(timestamp_value):
            return None
        
        try:
            # Handle OpenAQ timestamp dictionary format
            if isinstance(timestamp_value, dict):
                # OpenAQ returns: {'utc': '2016-03-06T20:00:00Z', 'local': '2016-03-06T12:00:00-08:00'}
                utc_timestamp = timestamp_value.get('utc')
                if utc_timestamp:
                    dt = pd.to_datetime(utc_timestamp, utc=True)
                    return dt.isoformat()
                else:
                    self.logger.warning(f"OpenAQ timestamp dict missing 'utc' field: {timestamp_value}")
                    return None
            
            # If it's already a datetime object
            elif isinstance(timestamp_value, datetime):
                return timestamp_value.isoformat()
            
            # If it's a string, parse and reformat
            elif isinstance(timestamp_value, str):
                dt = pd.to_datetime(timestamp_value, utc=True)
                return dt.isoformat()
            
            else:
                self.logger.warning(f"Unexpected timestamp type {type(timestamp_value)}: {timestamp_value}")
                return None
            
        except (ValueError, TypeError) as e:
            self.logger.warning(f"Could not format timestamp '{timestamp_value}': {e}")
            return None
    
    def insert_new_sensors(self, new_sensors: pd.DataFrame) -> bool:
        """
        Insert new sensors into BigQuery
        
        Args:
            new_sensors: DataFrame of new sensors to insert
            
        Returns:
            bool: True if insertion was successful
        """
        if new_sensors.empty:
            self.logger.info("No new sensors to insert")
            return True
        
        self.logger.info(f"Inserting {len(new_sensors)} new sensors")
        
        # Prepare data for insertion
        rows = self.prepare_sensors_for_insert(new_sensors, is_update=False)
        
        # Insert into BigQuery
        success = self.bq_manager.insert_rows(
            self.config.DATASET_ID,
            self.config.SENSOR_TABLE_ID,
            rows
        )
        
        if success:
            self.logger.info(f"Successfully inserted {len(new_sensors)} new sensors")
        else:
            self.logger.error(f"Failed to insert {len(new_sensors)} new sensors")
        
        return success
    
    def update_existing_sensors(self, updated_sensors: pd.DataFrame) -> bool:
        """
        Update existing sensors in BigQuery using individual UPDATE statements
        
        Args:
            updated_sensors: DataFrame of sensors to update
            
        Returns:
            bool: True if all updates were successful
        """
        if updated_sensors.empty:
            self.logger.info("No sensors to update")
            return True
        
        self.logger.info(f"Updating {len(updated_sensors)} existing sensors")
        
        success_count = 0
        total_sensors = len(updated_sensors)
        
        for _, sensor in updated_sensors.iterrows():
            if self._update_single_sensor(sensor):
                success_count += 1
            else:
                self.logger.error(f"Failed to update sensor {sensor.get('sensor_id')}")
        
        success = success_count == total_sensors
        
        if success:
            self.logger.info(f"Successfully updated all {total_sensors} sensors")
        else:
            self.logger.warning(f"Updated {success_count}/{total_sensors} sensors")
        
        return success
    
    def _update_single_sensor(self, sensor: pd.Series) -> bool:
        """Update a single sensor record"""
        sensor_id = sensor.get('sensor_id')
        
        try:
            # Format timestamps
            datetime_first = self._format_timestamp_for_bq(sensor.get('datetimeFirst'))
            datetime_last = self._format_timestamp_for_bq(sensor.get('datetimeLast'))
            
            # Build update query
            update_query = f"""
            UPDATE `{self.config.PROJECT_ID}.{self.config.DATASET_ID}.{self.config.SENSOR_TABLE_ID}`
            SET 
                location_name = @location_name,
                locality = @locality,
                is_mobile = @is_mobile,
                is_monitor = @is_monitor,
                lat = @lat,
                lon = @lon,
                datetimeFirst = @datetimeFirst,
                datetimeLast = @datetimeLast,
                updated_at = @updated_at
            WHERE sensor_id = @sensor_id
            """
            
            # Prepare query parameters
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("location_name", "STRING", sensor.get('location_name')),
                    bigquery.ScalarQueryParameter("locality", "STRING", sensor.get('locality')),
                    bigquery.ScalarQueryParameter("is_mobile", "BOOLEAN", sensor.get('is_mobile')),
                    bigquery.ScalarQueryParameter("is_monitor", "BOOLEAN", sensor.get('is_monitor')),
                    bigquery.ScalarQueryParameter("lat", "FLOAT64", float(sensor.get('lat')) if sensor.get('lat') is not None else None),
                    bigquery.ScalarQueryParameter("lon", "FLOAT64", float(sensor.get('lon')) if sensor.get('lon') is not None else None),
                    bigquery.ScalarQueryParameter("datetimeFirst", "TIMESTAMP", datetime_first),
                    bigquery.ScalarQueryParameter("datetimeLast", "TIMESTAMP", datetime_last),
                    bigquery.ScalarQueryParameter("updated_at", "TIMESTAMP", datetime.now(timezone.utc)),
                    bigquery.ScalarQueryParameter("sensor_id", "STRING", sensor_id),
                ]
            )
            
            # Execute update
            query_job = self.bq_manager.client.query(update_query, job_config=job_config)
            query_job.result()  # Wait for completion
            
            self.logger.debug(f"Successfully updated sensor {sensor_id}")
            return True
            
        except GoogleCloudError as e:
            self.logger.error(f"BigQuery error updating sensor {sensor_id}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error updating sensor {sensor_id}: {e}")
            return False
    
    def process_sensor_updates(self, fetched_sensors: pd.DataFrame) -> Dict[str, any]:
        """
        Main method to process sensor updates - orchestrates the entire workflow
        
        Args:
            fetched_sensors: DataFrame of sensors fetched from OpenAQ API
            
        Returns:
            dict: Results summary with counts and success status
        """
        self.logger.info("Starting sensor update processing")
        
        # Ensure table exists
        if not self.ensure_sensors_table_exists():
            return {
                "new_sensors": 0,
                "updated_sensors": 0,
                "total_processed": 0,
                "success": False,
                "error": "Failed to ensure sensors table exists"
            }
        
        # Get existing sensors
        existing_sensors = self.get_existing_sensors()
        
        # Compare and identify changes
        new_sensors, updated_sensors = self.compare_sensors(fetched_sensors, existing_sensors)
        
        # Process new sensors
        new_success = self.insert_new_sensors(new_sensors)
        
        # Process updated sensors
        update_success = self.update_existing_sensors(updated_sensors)
        
        # Calculate results
        overall_success = new_success and update_success
        total_processed = len(new_sensors) + len(updated_sensors)
        
        result = {
            "new_sensors": len(new_sensors) if new_success else 0,
            "updated_sensors": len(updated_sensors) if update_success else 0,
            "total_processed": total_processed,
            "success": overall_success,
            "fetched_count": len(fetched_sensors),
            "existing_count": len(existing_sensors)
        }
        
        self.logger.info(f"Sensor update processing complete: {result}")
        
        return result
    
    def get_sensor_statistics(self) -> Dict[str, any]:
        """Get statistics about sensors in the database"""
        try:
            if not self.bq_manager.table_exists(self.config.DATASET_ID, self.config.SENSOR_TABLE_ID):
                return {"error": "Sensors table does not exist"}
            
            stats_query = f"""
            SELECT 
                COUNT(*) as total_sensors,
                COUNT(DISTINCT location_id) as unique_locations,
                COUNT(DISTINCT owner_name) as unique_owners,
                COUNT(DISTINCT provider_name) as unique_providers,
                MIN(lat) as min_latitude,
                MAX(lat) as max_latitude,
                MIN(lon) as min_longitude,
                MAX(lon) as max_longitude,
                MIN(datetimeFirst) as earliest_data,
                MAX(datetimeLast) as latest_data,
                COUNTIF(is_mobile = true) as mobile_sensors,
                COUNTIF(is_monitor = true) as reference_monitors
            FROM `{self.config.PROJECT_ID}.{self.config.DATASET_ID}.{self.config.SENSOR_TABLE_ID}`
            """
            
            result_df = self.bq_manager.execute_query(stats_query)
            
            if result_df is not None and not result_df.empty:
                stats = result_df.iloc[0].to_dict()
                self.logger.info("Retrieved sensor statistics")
                return stats
            else:
                return {"error": "No statistics available"}
                
        except Exception as e:
            self.logger.error(f"Error getting sensor statistics: {e}")
            return {"error": str(e)}


# Example usage and testing
if __name__ == "__main__":
    from pipeline_config import PipelineConfig
    from logger import PipelineLogger
    from bigquery_manager import BigQueryManager
    
    print("=== Sensor Manager Test ===")
    
    # Initialize components
    config = PipelineConfig()
    logger_setup = PipelineLogger(config)
    bq_manager = BigQueryManager(config)
    sensor_manager = SensorManager(bq_manager, config)
    
    print("✓ Sensor Manager initialized")
    
    # Test table creation
    if sensor_manager.ensure_sensors_table_exists():
        print("✓ Sensors table ready")
    else:
        print("✗ Failed to create sensors table")
        exit(1)
    
    # Test loading existing sensors
    existing = sensor_manager.get_existing_sensors()
    print(f"✓ Loaded {len(existing)} existing sensors")
    
    # Test statistics
    stats = sensor_manager.get_sensor_statistics()
    if "error" not in stats:
        print(f"✓ Sensor statistics:")
        print(f"  Total sensors: {stats.get('total_sensors', 0)}")
        print(f"  Unique locations: {stats.get('unique_locations', 0)}")
        print(f"  Mobile sensors: {stats.get('mobile_sensors', 0)}")
        print(f"  Reference monitors: {stats.get('reference_monitors', 0)}")
    else:
        print(f"⚠ Statistics error: {stats['error']}")
    
    print("\n✓ Sensor Manager test completed!")