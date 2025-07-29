"""
config.py

Loads environment variables from the .env file and provides
secure access to sensitive configuration values such as
the GitHub Personal Access Token (PAT) for use in the project.
"""

from dotenv import load_dotenv
import os

load_dotenv()  # Loads variables from .env

GITHUB_PAT = os.getenv("GITHUB_PAT")
