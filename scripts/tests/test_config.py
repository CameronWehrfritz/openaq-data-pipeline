# tests/test_config.py
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pipeline_config import get_config

# Test all environment types
dev_config = get_config("development")
test_config = get_config("testing") 
prod_config = get_config("production")

print(f"Development PROJECT_ID: {dev_config.PROJECT_ID}")
print(f"Testing PROJECT_ID: {test_config.PROJECT_ID}")
print(f"Production PROJECT_ID: {prod_config.PROJECT_ID}")

# Test validation
try:
    prod_config.validate()
    print("Production config validation: PASSED")
except ValueError as e:
    print(f"Production config validation: FAILED - {e}")