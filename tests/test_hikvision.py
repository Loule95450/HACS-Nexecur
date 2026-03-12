"""
Tests for Nexecur Hikvision API Client
"""
import pytest
import json
import hashlib
import uuid
from unittest.mock import Mock, patch, AsyncMock
import sys
import os

# Add custom_components to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'custom_components', 'nexecur'))

from nexecur_api_hikvision import NexecurHikvisionClient


class TestHikvisionClient:
    """Test cases for Hikvision client"""

    @pytest.fixture
    def client(self):
        """Create a test client"""
        return NexecurHikvisionClient(
            phone="0612345678",
            password="testpassword",
            country_code="33",
            ssid="TestWiFi",
            device_name="Test Device"
        )

    def test_client_initialization_phone(self, client):
        """Test client is created with phone"""
        assert client._account == "330612345678"  # Country code + phone
        assert client._password == "testpassword"
        assert client._ssid == "TestWiFi"
        assert client._device_name == "Test Device"

    def test_client_initialization_email(self):
        """Test client accepts email as phone param (detected via @)"""
        # The client uses phone param but detects email via @ symbol
        client = NexecurHikvisionClient(
            phone="test@example.com",  # Pass email as phone param
            password="testpassword",
            country_code="33",
            ssid="TestWiFi"
        )
        assert "@" in client._account

    def test_format_account_phone(self):
        """Test phone number formatting"""
        client = NexecurHikvisionClient(
            phone="06 12 34 56 78",
            password="test",
            country_code="33",
            ssid="WiFi"
        )
        
        assert client._account == "330612345678"

    def test_format_account_email_unchanged(self):
        """Test email is not modified when passed as phone param"""
        # Email detected via @ in phone param
        result = NexecurHikvisionClient._format_account("33", "test@domain.com")
        assert result == "test@domain.com"

    def test_md5_hash(self, client):
        """Test MD5 hashing"""
        result = client._md5("teststring")
        expected = hashlib.md5("teststring".encode()).hexdigest()
        
        assert result == expected

    def test_feature_code_generation(self, client):
        """Test feature code is generated"""
        code = client._generate_feature_code()
        
        assert isinstance(code, str)
        assert len(code) == 32  # MD5 hex length

    @pytest.mark.skip(reason="Requires complex aiohttp mocking")
    @pytest.mark.asyncio
    async def test_login_success(self, client):
        """Test successful login"""
        mock_response = {
            "meta": {"code": "200"},
            "loginSession": {"sessionId": "test_session_123"},
            "loginUser": {"username": "330612345678", "customno": "cust123", "areaId": 1},
            "loginArea": {"apiDomain": "apiieu.guardingvision.com"}
        }
        
        with patch.object(client, '_session_ensure', new_callable=AsyncMock) as mock_session:
            mock_session.return_value = Mock()
            
            with patch('aiohttp.ClientSession.post') as mock_post:
                mock_post.return_value.__aenter__ = AsyncMock(return_value=Mock(
                    status=200,
                    json=AsyncMock(return_value=mock_response)
                ))
                mock_post.return_value.__aexit__ = AsyncMock(return_value=None)
                
                await client.async_login()
                
                assert client._session_id == "test_session_123"

    @pytest.mark.skip(reason="Requires complex aiohttp mocking")
    @pytest.mark.asyncio
    async def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        mock_response = {
            "meta": {"code": "401", "message": "Invalid credentials"}
        }
        
        with patch.object(client, '_session_ensure', new_callable=AsyncMock) as mock_session:
            mock_session.return_value = Mock()
            
            with patch('aiohttp.ClientSession.post') as mock_post:
                mock_post.return_value.__aenter__ = AsyncMock(return_value=Mock(
                    status=200,
                    json=AsyncMock(return_value=mock_response)
                ))
                mock_post.return_value.__aexit__ = AsyncMock(return_value=None)
                
                from nexecur_api_hikvision import NexecurAuthError
                
                with pytest.raises(NexecurAuthError) as exc_info:
                    await client.async_login()
                
                assert "Login failed" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_status_disarmed(self, client):
        """Test getting status when disarmed"""
        client._session_id = "test_session"
        client._current_device_serial = "DSI123456"
        
        mock_response = {
            "meta": {"code": "200"},
            "data": 'HTTP/1.1 200 OK\r\n\r\n{"AlarmHostStatus":{"SubSysList":[{"SubSys":{"id":1,"arming":"disarm"}}]}}'
        }
        
        with patch.object(client, '_execute_isapi_command', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = (True, mock_response["data"])
            
            status = await client.async_get_status()
            
            assert status.status == 0  # Disarmed

    @pytest.mark.asyncio
    async def test_get_status_armed_stay(self, client):
        """Test getting status when armed stay"""
        client._session_id = "test_session"
        client._current_device_serial = "DSI123456"
        
        mock_response = 'HTTP/1.1 200 OK\r\n\r\n{"AlarmHostStatus":{"SubSysList":[{"SubSys":{"id":1,"arming":"stay"}}]}}'
        
        with patch.object(client, '_execute_isapi_command', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = (True, mock_response)
            
            status = await client.async_get_status()
            
            assert status.status == 1  # Stay

    @pytest.mark.asyncio
    async def test_get_status_armed_away(self, client):
        """Test getting status when armed away"""
        client._session_id = "test_session"
        client._current_device_serial = "DSI123456"
        
        mock_response = 'HTTP/1.1 200 OK\r\n\r\n{"AlarmHostStatus":{"SubSysList":[{"SubSys":{"id":1,"arming":"away"}}]}}'
        
        with patch.object(client, '_execute_isapi_command', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = (True, mock_response)
            
            status = await client.async_get_status()
            
            assert status.status == 2  # Away


class TestDigestAuthentication:
    """Test digest authentication logic"""

    @pytest.fixture
    def client(self):
        return NexecurHikvisionClient(
            phone="0612345678",
            password="testpassword",
            country_code="33",
            ssid="TestWiFi"
        )

    def test_calculate_digest_auth(self, client):
        """Test digest auth calculation"""
        client._security_info = {
            "nonce": "test-nonce",
            "realm": "DVRNVRDVS"
        }
        client._user_info = {"username": "testuser"}
        
        digest = client._calculate_digest_auth("GET", "/test/uri", "test-nonce", "DVRNVRDVS")
        
        assert "Digest username=" in digest
        assert "realm=" in digest
        assert "nonce=" in digest

    def test_digest_auth_with_salts(self, client):
        """Test digest auth with password salts"""
        client._security_info = {
            "nonce": "test-nonce",
            "realm": "DVRNVRDVS",
            "salt": "salt1",
            "salt2": "salt2"
        }
        client._user_info = {"username": "testuser"}
        
        digest = client._calculate_digest_auth("POST", "/api/endpoint", "test-nonce", "DVRNVRDVS")
        
        assert digest.startswith("Digest ")


class TestISAPITunnel:
    """Test ISAPI tunnel functionality"""

    @pytest.fixture
    def client(self):
        return NexecurHikvisionClient(
            phone="0612345678",
            password="testpassword",
            country_code="33",
            ssid="TestWiFi"
        )

    @pytest.mark.skip(reason="Requires complex aiohttp mocking")
    @pytest.mark.asyncio
    async def test_send_isapi_request(self, client):
        """Test ISAPI request through tunnel"""
        client._session_id = "test_session"
        client._current_device_serial = "DSI123456"
        
        mock_response = {"meta": {"code": 200}, "data": "OK"}
        
        with patch.object(client, '_session_ensure', new_callable=AsyncMock) as mock_session:
            mock_session.return_value = Mock()
            
            with patch('aiohttp.ClientSession.post') as mock_post:
                mock_post.return_value.__aenter__ = AsyncMock(return_value=Mock(
                    status=200,
                    json=AsyncMock(return_value=mock_response)
                ))
                mock_post.return_value.__aexit__ = AsyncMock(return_value=None)
                
                result = await client._send_isapi("DSI123456", "POST", "/test/uri", {})
                
                assert result == mock_response


class TestArmCommands:
    """Test arm/disarm commands"""

    @pytest.fixture
    def client(self):
        c = NexecurHikvisionClient(
            phone="0612345678",
            password="testpassword",
            country_code="33",
            ssid="TestWiFi"
        )
        c._session_id = "test_session"
        c._current_device_serial = "DSI123456"
        return c

    @pytest.mark.asyncio
    async def test_set_armed_home(self, client):
        """Test arm stay"""
        with patch.object(client, '_execute_isapi_command', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = (True, "HTTP/1.1 200 OK")
            
            await client.async_set_armed_home()
            
            # Check correct payload was sent
            call_args = mock_exec.call_args
            assert "stay" in str(call_args)

    @pytest.mark.asyncio
    async def test_set_armed_away(self, client):
        """Test arm away"""
        with patch.object(client, '_execute_isapi_command', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = (True, "HTTP/1.1 200 OK")
            
            await client.async_set_armed_away()
            
            call_args = mock_exec.call_args
            assert "away" in str(call_args)
