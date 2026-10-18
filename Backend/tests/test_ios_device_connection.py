"""
Tests for iOS Device Connection Status
======================================
Tests to verify that device connection status updates correctly
when device is connected/disconnected.
"""

import pytest
import json
import subprocess
from unittest.mock import patch, MagicMock, Mock
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


class TestIOSDeviceConnection:
    """Test iOS device connection detection."""
    
    def test_device_connected_via_finder(self, client):
        """Test device detection via Finder when device is connected."""
        # Mock Finder check to return device
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = "Isaiah's iPhone\n"
        
        with patch('subprocess.run', return_value=mock_result):
            response = client.get("/api/import/ios/device")
            
            assert response.status_code == 200
            data = response.json()
            assert data["connected"] is True
            assert "iPhone" in data["name"] or "iOS" in data["name"]
            assert data["connection_type"] == "finder"
    
    def test_device_connected_via_usb(self, client):
        """Test device detection via USB when device is connected."""
        # Mock USB check to return device
        mock_usb_data = {
            "SPUSBDataType": [
                {
                    "_items": [
                        {
                            "_name": "iPhone",
                            "serial_num": "IOS_23A8464",
                            "product_id": "0x1234"
                        }
                    ]
                }
            ]
        }
        
        mock_result = Mock()
        mock_result.returncode = 0
        mock_result.stdout = json.dumps(mock_usb_data)
        
        with patch('subprocess.run', return_value=mock_result):
            response = client.get("/api/import/ios/device")
            
            assert response.status_code == 200
            data = response.json()
            assert data["connected"] is True
            assert "iPhone" in data["name"] or "iOS" in data["name"]
            assert data["connection_type"] == "usb"
    
    def test_device_not_connected(self, client):
        """Test device detection when device is NOT connected."""
        # Mock both checks to return no device
        mock_result_finder = Mock()
        mock_result_finder.returncode = 0
        mock_result_finder.stdout = ""  # No device found
        
        mock_result_usb = Mock()
        mock_result_usb.returncode = 0
        mock_result_usb.stdout = json.dumps({"SPUSBDataType": []})  # No USB devices
        
        def mock_subprocess_run(cmd, **kwargs):
            if "osascript" in cmd:
                return mock_result_finder
            elif "system_profiler" in cmd:
                return mock_result_usb
            return Mock()
        
        with patch('subprocess.run', side_effect=mock_subprocess_run):
            response = client.get("/api/import/ios/device")
            
            assert response.status_code == 200
            data = response.json()
            assert data["connected"] is False
    
    def test_device_disconnect_detection(self, client):
        """Test that disconnection is detected correctly."""
        # First call: device connected
        mock_result_connected = Mock()
        mock_result_connected.returncode = 0
        mock_result_connected.stdout = "Isaiah's iPhone\n"
        
        # Second call: device disconnected
        mock_result_disconnected = Mock()
        mock_result_disconnected.returncode = 0
        mock_result_disconnected.stdout = ""  # No device
        
        mock_result_usb_empty = Mock()
        mock_result_usb_empty.returncode = 0
        mock_result_usb_empty.stdout = json.dumps({"SPUSBDataType": []})
        
        call_count = [0]
        
        def mock_subprocess_run(cmd, **kwargs):
            call_count[0] += 1
            if "osascript" in cmd:
                if call_count[0] == 1:
                    return mock_result_connected
                else:
                    return mock_result_disconnected
            elif "system_profiler" in cmd:
                return mock_result_usb_empty
            return Mock()
        
        with patch('subprocess.run', side_effect=mock_subprocess_run):
            # First check: device connected
            response1 = client.get("/api/import/ios/device")
            assert response1.status_code == 200
            data1 = response1.json()
            assert data1["connected"] is True
            
            # Second check: device disconnected
            response2 = client.get("/api/import/ios/device")
            assert response2.status_code == 200
            data2 = response2.json()
            assert data2["connected"] is False
    
    def test_finder_check_fails_gracefully(self, client):
        """Test that Finder check failure doesn't break USB check."""
        # Mock Finder check to fail
        mock_result_finder = Mock()
        mock_result_finder.returncode = 1  # Finder check failed
        mock_result_finder.stdout = ""
        
        # Mock USB check to succeed
        mock_usb_data = {
            "SPUSBDataType": [
                {
                    "_items": [
                        {
                            "_name": "iPhone",
                            "serial_num": "IOS_23A8464"
                        }
                    ]
                }
            ]
        }
        mock_result_usb = Mock()
        mock_result_usb.returncode = 0
        mock_result_usb.stdout = json.dumps(mock_usb_data)
        
        def mock_subprocess_run(cmd, **kwargs):
            if "osascript" in cmd:
                return mock_result_finder
            elif "system_profiler" in cmd:
                return mock_result_usb
            return Mock()
        
        with patch('subprocess.run', side_effect=mock_subprocess_run):
            response = client.get("/api/import/ios/device")
            
            assert response.status_code == 200
            data = response.json()
            # Should still detect device via USB even if Finder fails
            assert data["connected"] is True
            assert data["connection_type"] == "usb"
    
    def test_usb_check_fails_gracefully(self, client):
        """Test that USB check failure doesn't break Finder check."""
        # Mock Finder check to succeed
        mock_result_finder = Mock()
        mock_result_finder.returncode = 0
        mock_result_finder.stdout = "Isaiah's iPhone\n"
        
        # Mock USB check to fail
        mock_result_usb = Mock()
        mock_result_usb.returncode = 1  # USB check failed
        mock_result_usb.stdout = ""
        
        def mock_subprocess_run(cmd, **kwargs):
            if "osascript" in cmd:
                return mock_result_finder
            elif "system_profiler" in cmd:
                return mock_result_usb
            return Mock()
        
        with patch('subprocess.run', side_effect=mock_subprocess_run):
            response = client.get("/api/import/ios/device")
            
            assert response.status_code == 200
            data = response.json()
            # Should still detect device via Finder even if USB fails
            assert data["connected"] is True
            assert data["connection_type"] == "finder"
    
    def test_both_checks_fail_returns_not_connected(self, client):
        """Test that when both checks fail, device is reported as not connected."""
        # Mock both checks to fail
        mock_result_finder = Mock()
        mock_result_finder.returncode = 1
        mock_result_finder.stdout = ""
        
        mock_result_usb = Mock()
        mock_result_usb.returncode = 1
        mock_result_usb.stdout = ""
        
        def mock_subprocess_run(cmd, **kwargs):
            if "osascript" in cmd:
                return mock_result_finder
            elif "system_profiler" in cmd:
                return mock_result_usb
            return Mock()
        
        with patch('subprocess.run', side_effect=mock_subprocess_run):
            response = client.get("/api/import/ios/device")
            
            assert response.status_code == 200
            data = response.json()
            assert data["connected"] is False
    
    def test_timeout_handling(self, client):
        """Test that timeouts are handled gracefully."""
        # Mock subprocess to raise timeout
        with patch('subprocess.run', side_effect=subprocess.TimeoutExpired("cmd", 10)):
            response = client.get("/api/import/ios/device")
            
            # Should return not connected on timeout
            assert response.status_code == 200
            data = response.json()
            assert data["connected"] is False
    
    def test_invalid_json_from_usb_check(self, client):
        """Test that invalid JSON from USB check is handled."""
        # Mock Finder to return no device
        mock_result_finder = Mock()
        mock_result_finder.returncode = 0
        mock_result_finder.stdout = ""
        
        # Mock USB to return invalid JSON
        mock_result_usb = Mock()
        mock_result_usb.returncode = 0
        mock_result_usb.stdout = "invalid json {"
        
        def mock_subprocess_run(cmd, **kwargs):
            if "osascript" in cmd:
                return mock_result_finder
            elif "system_profiler" in cmd:
                return mock_result_usb
            return Mock()
        
        with patch('subprocess.run', side_effect=mock_subprocess_run):
            response = client.get("/api/import/ios/device")
            
            # Should handle gracefully and return not connected
            assert response.status_code == 200
            data = response.json()
            assert data["connected"] is False


class TestConnectionStatusPersistence:
    """Test that connection status doesn't persist incorrectly."""
    
    def test_status_changes_on_each_request(self, client):
        """Test that each API call checks current status, not cached."""
        # Simulate device being connected then disconnected
        states = [
            (True, "Isaiah's iPhone\n"),  # First call: connected
            (False, ""),  # Second call: disconnected
            (False, ""),  # Third call: still disconnected
        ]
        
        state_index = [0]
        
        def mock_subprocess_run(cmd, **kwargs):
            if "osascript" in cmd:
                mock_result = Mock()
                mock_result.returncode = 0
                mock_result.stdout = states[state_index[0]][1]
                state_index[0] = (state_index[0] + 1) % len(states)
                return mock_result
            elif "system_profiler" in cmd:
                mock_result = Mock()
                mock_result.returncode = 0
                # USB check should also reflect current state
                if states[state_index[0] - 1 if state_index[0] > 0 else 0][0]:
                    mock_result.stdout = json.dumps({
                        "SPUSBDataType": [{"_items": [{"_name": "iPhone"}]}]
                    })
                else:
                    mock_result.stdout = json.dumps({"SPUSBDataType": []})
                return mock_result
            return Mock()
        
        with patch('subprocess.run', side_effect=mock_subprocess_run):
            # First call: should be connected
            response1 = client.get("/api/import/ios/device")
            assert response1.json()["connected"] is True
            
            # Second call: should be disconnected
            response2 = client.get("/api/import/ios/device")
            assert response2.json()["connected"] is False
            
            # Third call: should still be disconnected
            response3 = client.get("/api/import/ios/device")
            assert response3.json()["connected"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

