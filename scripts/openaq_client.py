"""
OpenAQ Client Module
Handles all OpenAQ API interactions for the data pipeline
"""

import time
import logging
import requests
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

try:
    from pipeline_config import PipelineConfig
except ModuleNotFoundError:
    from scripts.pipeline_config import PipelineConfig

class OpenAQClient:
    """Handles all OpenAQ API operations with robust error handling and retry logic"""
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.session = self._create_session()
        self.request_count = 0
        self.start_time = datetime.now()
    
    def __str__(self):
        uptime = (datetime.now() - self.start_time).seconds
        return f"OpenAQClient(requests: {self.request_count}, API: {self.config.OPENAQ_API_BASE}, uptime: {uptime}s, API key: {bool(self.config.OPENAQ_API_KEY)})"

    def _create_session(self) -> requests.Session:
        """Create a requests session with proper headers and configuration"""
        session = requests.Session()
        
        # Set headers
        session.headers.update({
            "accept": "application/json",
            "X-API-Key": self.config.OPENAQ_API_KEY,
            "User-Agent": f"OpenAQ-Pipeline/1.0 (Data Engineering Project)"
        })
        
        # Validate API key
        if not self.config.OPENAQ_API_KEY or len(self.config.OPENAQ_API_KEY) < 10:
            raise ValueError(
                "OpenAQ API key not found or invalid. "
                "Please set OPENAQ_API_KEY in your .env file"
            )
        
        self.logger.info("OpenAQ API client initialized")
        return session
    
    def _make_request(self, url: str, params: Dict, attempt: int = 1) -> Optional[Dict]:
        """
        Make API request with comprehensive retry logic and error handling
        
        Args:
            url: API endpoint URL
            params: Query parameters
            attempt: Current attempt number (for recursive retries)
            
        Returns:
            dict: JSON response data, or None if all retries failed
        """
        try:
            self.logger.debug(f"API request (attempt {attempt}): {url} with params {params}")
            
            # Make the request
            response = self.session.get(
                url,
                params=params,
                timeout=self.config.API_TIMEOUT
            )
            
            # Track request count for rate limiting awareness
            self.request_count += 1
            
            # Handle different HTTP status codes
            if response.status_code == 200:
                self.logger.debug(f"API request successful (attempt {attempt})")
                return response.json()
                
            elif response.status_code == 429:  # Rate limited
                self.logger.warning(f"Rate limited by OpenAQ API (attempt {attempt})")
                if attempt <= self.config.MAX_RETRIES:
                    wait_time = self.config.RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                    self.logger.info(f"Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    return self._make_request(url, params, attempt + 1)
                
            elif response.status_code == 401:  # Unauthorized
                raise requests.exceptions.HTTPError(
                    f"Unauthorized (401): Invalid API key. Please check your OPENAQ_API_KEY"
                )
                
            elif response.status_code == 403:  # Forbidden
                raise requests.exceptions.HTTPError(
                    f"Forbidden (403): API key may not have required permissions"
                )
            
            elif response.status_code == 404:  # Not Found
                self.logger.warning(f"Resource not found (404): {url}")
                raise requests.exceptions.HTTPError(
                    f"API endpoint not found (404): {url} may be invalid or deprecated"
                )
            
            elif response.status_code == 408:  # Request Timeout
                self.logger.warning(f"Server timeout (408) - query too complex (attempt {attempt})")
                if attempt <= self.config.MAX_RETRIES:
                    time.sleep(self.config.RETRY_DELAY * attempt)  # Linear backoff
                    return self._make_request(url, params, attempt + 1)
            
            elif response.status_code == 422:  # Unprocessable content
                self.logger.error(f"Invalid query parameters (422): {params}")
                raise requests.exceptions.HTTPError(
                    f"Unprocessable request (422): Query parameters may be invalid"
                )

            elif response.status_code >= 500:  # Server errors
                self.logger.warning(f"Server error {response.status_code} (attempt {attempt})")
                if attempt <= self.config.MAX_RETRIES:
                    wait_time = self.config.RETRY_DELAY * attempt   # Linear backoff
                    time.sleep(wait_time)
                    return self._make_request(url, params, attempt + 1)
                    
            else:
                self.logger.error(f"Unexpected status code: {response.status_code}")
                self.logger.error(f"Response: {response.text[:200]}...")
            
            # If we get here, the request failed
            response.raise_for_status()
            
        except requests.exceptions.Timeout:
            self.logger.warning(f"Request timeout (attempt {attempt}/{self.config.MAX_RETRIES})")
            if attempt <= self.config.MAX_RETRIES:
                time.sleep(self.config.RETRY_DELAY * attempt)   # Linear backoff
                return self._make_request(url, params, attempt + 1)
                
        except requests.exceptions.ConnectionError as e:
            self.logger.warning(f"Connection error (attempt {attempt}): {e}")
            if attempt <= self.config.MAX_RETRIES:
                time.sleep(self.config.RETRY_DELAY * attempt)   # Linear backoff
                return self._make_request(url, params, attempt + 1)
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed (attempt {attempt}): {e}")
            if attempt <= self.config.MAX_RETRIES:
                time.sleep(self.config.RETRY_DELAY * (2 ** attempt))   # Exponential backoff
                return self._make_request(url, params, attempt + 1)
        
        self.logger.error(f"All retry attempts failed for {url}")
        return None
    
    def _is_in_california(self, lat: float, lon: float) -> bool:
        """Check if coordinates are within California bounding box"""
        return (self.config.CA_LAT_MIN <= lat <= self.config.CA_LAT_MAX and 
                self.config.CA_LON_MIN <= lon <= self.config.CA_LON_MAX)
    
    def _validate_sensor_data(self, sensor_data: Dict) -> bool:
        """
        Validate sensor data has required fields and reasonable values
        
        Args:
            sensor_data: Dictionary containing sensor information
            
        Returns:
            bool: True if sensor data is valid
        """
        required_fields = self.config.REQUIRED_SENSOR_FIELDS
        
        # Check required fields exist and are not None/empty
        for field in required_fields:
            value = sensor_data.get(field)
            if value is None or value == "":
                self.logger.warning(f"Sensor missing required field '{field}': {sensor_data.get('sensor_id', 'unknown')}")
                return False
        
        # Validate coordinate ranges
        lat = sensor_data.get("lat")
        lon = sensor_data.get("lon")
        
        if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
            self.logger.warning(f"Invalid coordinate types for sensor {sensor_data.get('sensor_id')}")
            return False
        
        if not (-90 <= lat <= 90):
            self.logger.warning(f"Invalid latitude {lat} for sensor {sensor_data.get('sensor_id')}")
            return False
            
        if not (-180 <= lon <= 180):
            self.logger.warning(f"Invalid longitude {lon} for sensor {sensor_data.get('sensor_id')}")
            return False
        
        return True
    
    def fetch_pm25_ca_sensors(self) -> pd.DataFrame:
        """
        Fetch PM2.5 sensor metadata for California with comprehensive error handling
        
        Returns:
            pandas.DataFrame: DataFrame containing sensor metadata
        """
        url = f"{self.config.OPENAQ_API_BASE}/locations"
        params = {
            "country": "US",
            "parameters": "pm25",
            "limit": self.config.API_REQUEST_LIMIT,
            "page": 1
        }
        
        sensors = []
        total_locations_processed = 0
        ca_locations_found = 0
        
        self.logger.info("Starting PM2.5 sensor discovery for California")
        self.logger.info(f"Using API endpoint: {url}")
        self.logger.info(f"Request limit per page: {self.config.API_REQUEST_LIMIT}")
        
        start_time = time.time()
        
        while True:
            # Make API request
            data = self._make_request(url, params)
            if not data:
                self.logger.error("Failed to fetch data from OpenAQ API - aborting")
                break
            
            # Process response
            locations = data.get("results", [])
            total_locations_processed += len(locations)
            
            if not locations:
                self.logger.warning(f"No locations returned on page {params['page']}")
                break
            
            # Process each location
            for loc in locations:
                try:
                    # Extract coordinates safely
                    coords = loc.get("coordinates", {})
                    lat = coords.get("latitude")
                    lon = coords.get("longitude")
                    
                    if lat is None or lon is None:
                        continue
                    
                    # Check if location is in California
                    if not self._is_in_california(lat, lon):
                        continue
                    
                    ca_locations_found += 1
                    
                    # Extract nested objects safely with defaults
                    country = loc.get("country") or {}
                    owner = loc.get("owner") or {}
                    provider = loc.get("provider") or {}
                    
                    # Process sensors at this location
                    for sensor in loc.get("sensors", []):
                        if sensor.get("parameter", {}).get("name") == "pm25":
                            sensor_data = {
                                "sensor_id": sensor.get("id"),
                                "location_id": loc.get("id"),
                                "location_name": loc.get("name"),
                                "locality": loc.get("locality"),
                                "timezone": loc.get("timezone"),
                                "country_id": country.get("id"),
                                "country_code": country.get("code"),
                                "country_name": country.get("name"),
                                "owner_id": owner.get("id"),
                                "owner_name": owner.get("name"),
                                "provider_id": provider.get("id"),
                                "provider_name": provider.get("name"),
                                "is_mobile": loc.get("isMobile"),
                                "is_monitor": loc.get("isMonitor"),
                                "lat": lat,
                                "lon": lon,
                                "datetimeFirst": loc.get("datetimeFirst"),
                                "datetimeLast": loc.get("datetimeLast")
                            }
                            
                            # Validate sensor data before adding
                            if self._validate_sensor_data(sensor_data):
                                sensors.append(sensor_data)
                            
                except Exception as e:
                    self.logger.warning(f"Error processing location {loc.get('id', 'unknown')}: {e}")
                    continue
            
            # Check pagination
            current_page = params["page"]
            self.logger.info(f"Page {current_page}: {len(locations)} locations, "
                           f"{ca_locations_found} CA locations, {len(sensors)} PM2.5 sensors found so far")
            
            # Check if we should continue
            if len(locations) < self.config.API_REQUEST_LIMIT:
                # Got fewer locations than requested - this is the last page
                break
                
            params["page"] += 1
            
            # Be nice to the API - small delay between requests
            time.sleep(0.1)
        
        # Log final statistics
        duration = time.time() - start_time
        self.logger.info(f"Sensor discovery completed in {duration:.2f}s:")
        self.logger.info(f"  • Total locations processed: {total_locations_processed}")
        self.logger.info(f"  • California locations found: {ca_locations_found}")
        self.logger.info(f"  • PM2.5 sensors found: {len(sensors)}")
        self.logger.info(f"  • API requests made: {self.request_count}")
        self.logger.info(f"  • Average response time: {duration/self.request_count:.2f}s per request")
        
        return pd.DataFrame(sensors)
    
    def fetch_sensor_hourly_measurements (self, sensor_id: str, start_date: str = None, 
                                 end_date: str = None, limit: int = 1000) -> pd.DataFrame:
        """
        Fetch hourly measurements for a specific sensor (for future use)
        
        Uses OpenAQ v3 endpoint: /v3/sensors/{sensor_id}/measurements/hourly
        Returns hourly-averaged measurement data rather than raw sensor readings.

        Args:
            sensor_id: The sensor ID to fetch data for
            start_date: Start datetime in ISO format (YYYY-MM-DDTHH:MM:SS)
            end_date: End datetime in ISO format (YYYY-MM-DDTHH:MM:SS)
            limit: Maximum number of measurements to fetch

        Returns:
            pandas.DataFrame: Sensor measurements
        """
        url = f"{self.config.OPENAQ_API_BASE}/sensors/{sensor_id}/measurements/hourly"
        params = {
            "limit": min(limit, self.config.API_REQUEST_LIMIT)
        }
        
        if start_date:
            params["datetime_from"] = start_date
        if end_date:
            params["datetime_to"] = end_date
        
        self.logger.info(f"Fetching hourly measurements for sensor {sensor_id}")
        
        data = self._make_request(url, params)
        if not data:
            self.logger.error(f"Failed to fetch hourly measurements for sensor {sensor_id}")
            return pd.DataFrame()
        
        measurements = data.get("results", [])
        self.logger.info(f"Retrieved {len(measurements)} hourly measurements for sensor {sensor_id}")
        
        return pd.DataFrame(measurements)
    
    def get_api_stats(self) -> Dict:
        """Get statistics about API usage during this session"""
        duration = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "requests_made": self.request_count,
            "session_duration_seconds": duration,
            "avg_requests_per_minute": (self.request_count / duration * 60) if duration > 0 else 0,
            "start_time": self.start_time.isoformat(),
            "api_base_url": self.config.OPENAQ_API_BASE
        }


# Utility functions
def check_api_connection(config: PipelineConfig) -> Tuple[bool, str]:
    """Check if OpenAQ API is accessible with current credentials
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        client = OpenAQClient(config)
        # Use the public fetch method with minimal params
        result = client.fetch_pm25_ca_sensors()
        return (True, f"Connection successful, found {len(result)} sensors")
    except Exception as e:
        return (False, f"Connection failed: {str(e)}")
    
        # url = f"{config.OPENAQ_API_BASE}/locations"
        # params = {"limit": 1, "page": 1}
        # result = client._make_request(url, params)
        # return result is not None
        
    # except Exception as e:
    #     logging.getLogger(__name__).error(f"API connection test failed: {e}")
    #     return False


# Example usage and testing
if __name__ == "__main__":
    from pipeline_config import PipelineConfig
    from logger import PipelineLogger
    
    print("=== OpenAQ Client Test ===")
    
    # Initialize with test configuration
    config = PipelineConfig()
    config.API_REQUEST_LIMIT = 50  # Smaller limit for testing
    
    # Setup logging
    logger_setup = PipelineLogger(config)
    
    # Test API connection
    print("Testing API connection...")
    if check_api_connection(config):
        print("✓ API connection successful")
    else:
        print("✗ API connection failed")
        exit(1)
    
    # Initialize client
    client = OpenAQClient(config)
    
    # Test sensor fetching
    print("\nFetching California PM2.5 sensors...")
    try:
        sensors_df = client.fetch_pm25_ca_sensors()
        
        if not sensors_df.empty:
            print(f"✓ Successfully fetched {len(sensors_df)} sensors")
            print(f"\nSample sensor data:")
            sample = sensors_df.iloc[0]
            print(f"  ID: {sample['sensor_id']}")
            print(f"  Location: {sample['location_name']}")
            print(f"  Coordinates: ({sample['lat']}, {sample['lon']})")
            print(f"  Last Data: {sample['datetimeLast']}")
            
            # Show geographic distribution
            print(f"\nGeographic distribution:")
            print(f"  Latitude range: {sensors_df['lat'].min():.2f} to {sensors_df['lat'].max():.2f}")
            print(f"  Longitude range: {sensors_df['lon'].min():.2f} to {sensors_df['lon'].max():.2f}")
            
        else:
            print("⚠ No sensors found (unexpected)")
            
    except Exception as e:
        print(f"✗ Sensor fetching failed: {e}")
    
    # Show API statistics
    stats = client.get_api_stats()
    print(f"\nAPI Usage Statistics:")
    print(f"  Requests made: {stats['requests_made']}")
    print(f"  Session duration: {stats['session_duration_seconds']:.1f}s")
    print(f"  Avg requests/min: {stats['avg_requests_per_minute']:.1f}")
    
    print("\n✓ OpenAQ Client test completed!")