#!/usr/bin/env python3
"""
Deep Debug Script for OpenAQ API Issues
Investigates why no California sensors are being found
"""

import json
import requests
from pipeline_config import PipelineConfig
from config import OPENAQ_API_KEY

def test_raw_api_call():
    """Test raw API call to see actual response structure"""
    print("🔍 Testing Raw OpenAQ API Call...")
    
    url = "https://api.openaq.org/v3/locations"
    headers = {
        "accept": "application/json",
        "X-API-Key": OPENAQ_API_KEY
    }
    params = {
        "country": "US",
        "parameters": "pm25",
        "limit": 10,
        "page": 1
    }
    
    try:
        print(f"📡 Making request to: {url}")
        print(f"📋 Parameters: {params}")
        
        response = requests.get(url, headers=headers, params=params)
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n📄 API Response Structure:")
            print(f"Keys in response: {list(data.keys())}")
            
            if 'results' in data:
                results = data['results']
                print(f"Number of locations: {len(results)}")
                
                if results:
                    # Examine first location in detail
                    first_location = results[0]
                    print(f"\n🏠 First Location Structure:")
                    print(json.dumps(first_location, indent=2)[:1000] + "..." if len(str(first_location)) > 1000 else json.dumps(first_location, indent=2))
                    
                    # Check coordinates
                    coords = first_location.get("coordinates", {})
                    lat = coords.get("latitude")
                    lon = coords.get("longitude")
                    
                    print(f"\n📍 Geographic Analysis:")
                    print(f"Sample coordinates: lat={lat}, lon={lon}")
                    
                    # Check all locations for their coordinates
                    us_locations = []
                    ca_locations = []
                    
                    for loc in results:
                        coords = loc.get("coordinates", {})
                        lat = coords.get("latitude")
                        lon = coords.get("longitude")
                        
                        if lat is not None and lon is not None:
                            us_locations.append((lat, lon, loc.get("name", "Unknown")))
                            
                            # California bounding box check
                            if 32.5 <= lat <= 42.0 and -124.5 <= lon <= -114.0:
                                ca_locations.append((lat, lon, loc.get("name", "Unknown")))
                    
                    print(f"\n🗺️ Geographic Distribution:")
                    print(f"US locations with coordinates: {len(us_locations)}")
                    print(f"California locations: {len(ca_locations)}")
                    
                    if us_locations:
                        print(f"\n📍 Sample US Location Coordinates:")
                        for i, (lat, lon, name) in enumerate(us_locations[:5]):
                            in_ca = "✅ IN CA" if 32.5 <= lat <= 42.0 and -124.5 <= lon <= -114.0 else "❌ NOT CA"
                            print(f"  {i+1}. {name}: ({lat}, {lon}) {in_ca}")
                    
                    if ca_locations:
                        print(f"\n✅ California Locations Found:")
                        for lat, lon, name in ca_locations:
                            print(f"  • {name}: ({lat}, {lon})")
                    else:
                        print(f"\n❌ No California locations in this sample")
                        print(f"🔍 This suggests:")
                        print(f"   1. Need to check more pages of results")
                        print(f"   2. California sensors might be on later pages")
                        print(f"   3. Geographic distribution has changed")
                
            if 'meta' in data:
                meta = data['meta']
                print(f"\n📈 Pagination Info:")
                print(f"Current page: {meta.get('page', 'unknown')}")
                print(f"Total pages: {meta.get('totalPages', 'unknown')}")
                print(f"Total results: {meta.get('found', 'unknown')}")
                
        else:
            print(f"❌ API request failed")
            print(f"Response: {response.text[:500]}")
            
    except Exception as e:
        print(f"❌ Error testing API: {e}")

def test_california_specific_search():
    """Try more specific searches for California data"""
    print(f"\n🔍 Testing California-Specific Searches...")
    
    searches = [
        # Try different parameter combinations
        {"country": "US", "parameters": "pm25", "limit": 20},
        {"country": "US", "limit": 50},  # No parameter filter
        {"parameters": "pm25", "limit": 50},  # No country filter
        {"limit": 100},  # No filters at all
    ]
    
    headers = {
        "accept": "application/json", 
        "X-API-Key": OPENAQ_API_KEY
    }
    
    for i, params in enumerate(searches, 1):
        print(f"\n🧪 Test {i}: {params}")
        
        try:
            response = requests.get("https://api.openaq.org/v3/locations", 
                                  headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', [])
                
                ca_count = 0
                sample_locations = []
                
                for loc in results:
                    coords = loc.get("coordinates", {})
                    lat = coords.get("latitude")
                    lon = coords.get("longitude")
                    name = loc.get("name", "Unknown")
                    
                    if lat is not None and lon is not None:
                        sample_locations.append((lat, lon, name))
                        
                        # Check if in California
                        if 32.5 <= lat <= 42.0 and -124.5 <= lon <= -114.0:
                            ca_count += 1
                
                print(f"   📊 Results: {len(results)} locations, {ca_count} in California")
                
                if sample_locations:
                    print(f"   📍 Sample locations:")
                    for j, (lat, lon, name) in enumerate(sample_locations[:3]):
                        print(f"      {j+1}. {name}: ({lat}, {lon})")
                        
                if ca_count > 0:
                    print(f"   ✅ FOUND CALIFORNIA SENSORS!")
                    break
                    
            else:
                print(f"   ❌ Failed: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Error: {e}")

def check_api_documentation():
    """Check if API documentation endpoint is available"""
    print(f"\n📚 Checking API Documentation...")
    
    try:
        # Try to get API info/documentation
        headers = {"accept": "application/json", "X-API-Key": OPENAQ_API_KEY}
        
        # Some APIs have info endpoints
        info_urls = [
            "https://api.openaq.org/v3",
            "https://api.openaq.org/v3/info", 
            "https://api.openaq.org/v3/countries",
            "https://api.openaq.org/v3/parameters"
        ]
        
        for url in info_urls:
            try:
                response = requests.get(url, headers=headers, timeout=10)
                if response.status_code == 200:
                    print(f"✅ {url}: Available")
                    data = response.json()
                    print(f"   Keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
                else:
                    print(f"❌ {url}: {response.status_code}")
            except:
                print(f"❌ {url}: Failed")
                
    except Exception as e:
        print(f"❌ Error checking documentation: {e}")

if __name__ == "__main__":
    print("🔬 DEEP API INVESTIGATION")
    print("=" * 50)
    
    test_raw_api_call()
    test_california_specific_search() 
    check_api_documentation()
    
    print(f"\n🎯 SUMMARY:")
    print(f"If California sensors were found in any test above,")
    print(f"the issue is with our filtering logic.")
    print(f"If NO California sensors found anywhere,")
    print(f"the API data distribution may have changed.")