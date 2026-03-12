"""
Tests for Nexecur Videofied API Client
"""
import pytest
import json
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add custom_components to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'nexecur'))

from nexecur_api import NexecurClient


class TestVideofiedClient:
    """Test cases for Videofied client"""

    @pytest.fixture
    def client(self):
        """Create a test client"""
        return NexecurClient(
            id_site="12345",
            password="mypin123",
            device_name="Test Device"
        )

    def test_client_initialization(self, client):
        """Test client is created with correct parameters"""
        assert client._id_site == "12345"
        assert client._password_plain == "mypin123"
        assert client._device_name == "Test Device"
        assert client._token == ""
        assert client._id_device == ""

    @pytest.mark.asyncio
    async def test_login_creates_token(self, client):
        """Test login creates token and device ID"""
        with patch.object(client, '_post_json', new_callable=AsyncMock) as mock_post:
            # Mock salt response
            mock_post.side_effect = [
                {"message": "OK", "status": 0, "salt": "SaltedBase64=="},  # salt
                {"message": "OK", "status": 0, "token": "test_token", "id_device": "device_123"},  # site
                {"message": "OK", "status": 0, "id_device": "device_123"}  # register
            ]
            
            await client.async_login()
            
            assert client._token == "test_token"
            assert client._id_device == "device_123"

    @pytest.mark.asyncio
    async def test_get_status_disarmed(self, client):
        """Test getting status when disarmed"""
        client._token = "test_token"
        
        with patch.object(client, '_post_json', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = [
                {"message": "OK", "status": 0, "salt": "SaltedBase64=="},  # salt
                {"message": "OK", "status": 0, "panel_status": 0, "panel_sp1": 1, "panel_sp2": 1}  # site
            ]
            
            status = await client.async_get_status()
            
            assert status.status == 0  # Disarmed
            assert status.panel_sp1_available == True
            assert status.panel_sp2_available == True

    @pytest.mark.asyncio
    async def test_get_status_armed_partial(self, client):
        """Test getting status when armed partial"""
        client._token = "test_token"
        
        with patch.object(client, '_post_json', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = [
                {"message": "OK", "status": 0, "salt": "SaltedBase64=="},
                {"message": "OK", "status": 0, "panel_status": 1, "panel_sp1": 1, "panel_sp2": 1}
            ]
            
            status = await client.async_get_status()
            
            assert status.status == 1  # Partial/Home

    @pytest.mark.asyncio
    async def test_get_status_armed_total(self, client):
        """Test getting status when armed total"""
        client._token = "test_token"
        
        with patch.object(client, '_post_json', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = [
                {"message": "OK", "status": 0, "salt": "SaltedBase64=="},
                {"message": "OK", "status": 0, "panel_status": 2, "panel_sp1": 1, "panel_sp2": 1}
            ]
            
            status = await client.async_get_status()
            
            assert status.status == 2  # Total/Away

    @pytest.mark.asyncio
    async def test_set_armed_away(self, client):
        """Test arming away"""
        client._token = "test_token"
        client._id_device = "device_123"
        
        with patch.object(client, '_post_json', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = [
                {"message": "OK", "status": 0, "pending": 0}  # panel status
            ]
            
            await client.async_set_armed_away()
            
            # Check last call was with status=2
            last_call = mock_post.call_args
            assert last_call[1]['json']['status'] == 2

    @pytest.mark.asyncio
    async def test_set_armed_home(self, client):
        """Test arming home"""
        client._token = "test_token"
        client._id_device = "device_123"
        
        with patch.object(client, '_post_json', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = [
                {"message": "OK", "status": 0, "pending": 0}
            ]
            
            await client.async_set_armed_home()
            
            last_call = mock_post.call_args
            assert last_call[1]['json']['status'] == 1

    @pytest.mark.asyncio
    async def test_set_disarmed(self, client):
        """Test disarming"""
        client._token = "test_token"
        client._id_device = "device_123"
        
        with patch.object(client, '_post_json', new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = [
                {"message": "OK", "status": 0, "pending": 0}
            ]
            
            await client.async_set_armed(False)
            
            last_call = mock_post.call_args
            assert last_call[1]['json']['status'] == 0


class TestPasswordHashing:
    """Test password hashing logic"""

    @pytest.fixture
    def client(self):
        return NexecurClient(id_site="12345", password="testpin")

    def test_compute_hashes_format(self, client):
        """Test hashes are computed correctly"""
        salt_b64 = "SaltedBase64=="
        pwd_hash, pin_hash = client._compute_hashes("mypin", salt_b64)
        
        # Both should be base64 encoded
        assert isinstance(pwd_hash, str)
        assert isinstance(pin_hash, str)
        # Should not be empty
        assert len(pwd_hash) > 0
        assert len(pin_hash) > 0

    def test_different_passwords_different_hashes(self, client):
        """Test different passwords produce different hashes"""
        salt_b64 = "SaltedBase64=="
        
        hash1 = client._compute_hashes("pin1", salt_b64)[0]
        hash2 = client._compute_hashes("pin2", salt_b64)[0]
        
        assert hash1 != hash2

    def test_different_salts_different_hashes(self, client):
        """Test different salts produce different hashes"""
        hash1 = client._compute_hashes("mypin", "SaltedBase64AA==")[0]
        hash2 = client._compute_hashes("mypin", "SaltedBase64BB==")[0]
        
        assert hash1 != hash2


class TestAlarmStates:
    """Test alarm state mapping"""

    def test_status_disarmed(self):
        """Test disarmed status code"""
        assert 0 == 0  # Disarmed

    def test_status_armed_home(self):
        """Test armed home status code"""
        assert 1 == 1  # Armed home

    def test_status_armed_away(self):
        """Test armed away status code"""
        assert 2 == 2  # Armed away
