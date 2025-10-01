"""
Unit tests for OpenAQ Client
"""

import pytest
from scripts.openaq_client import check_api_connection
from scripts.pipeline_config import PipelineConfig


def test_check_api_connection_returns_tuple():
    """Test that test_api_connection returns a tuple with (bool, str)"""
    config = PipelineConfig()
    result = check_api_connection(config)
    
    # Check it returns a tuple
    assert isinstance(result, tuple)
    assert len(result) == 2
    
    # Check types of tuple elements
    success, message = result
    assert isinstance(success, bool)
    assert isinstance(message, str)


def test_check_api_connection_success_message():
    """Test that successful connection returns expected message format"""
    config = PipelineConfig()
    success, message = check_api_connection(config)
    
    if success:
        assert "Connection successful" in message
        assert "sensors" in message.lower()
    else:
        pytest.skip("API connection failed - may be network issue")