"""
config.py

Loads environment variables from the .env file and provides
secure access to sensitive configuration values for use in 
the project.
"""

from dotenv import load_dotenv
import os

# Load .env variables when config.py is first imported
load_dotenv()

# Expose secrets as constants
GITHUB_PAT = os.getenv("GITHUB_PAT") # Github token
OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY") # OpenAQ API token
