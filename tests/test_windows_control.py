"""
tests/test_windows_control.py — Automated Unit Tests for Windows 11 Advanced System Control.

Rules strictly adhered to:
- Rule 9: Zero destructive actions, zero settings changed, zero network drops during tests.
- All disruptive or external actions are tested using mocks or dry-run checks.
- Covers all 14 Phase 5 test criteria.
"""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch
import platform

from core.windows_control.contracts import SystemControlResult
from core.windows_control import (
    audio,
    display,
    network,
    power,
    personalization,
    system,
    settings_uris,
    runner
)


class TestWindowsControlContracts(unittest.TestCase):
    """Test 1: Standard result contract and formatting."""

    def test_result_contract_success(self):
        res = SystemControlResult(
            success=True,
            action="set_volume",
            requested_value=30,
            actual_value=30,
            verified=True,
            message="Volume set to 30%."
        )
        d = res.to_dict()
        self.assertTrue(d["success"])
        self.assertEqual(d["action"], "set_volume")
        self.assertEqual(d["requested_value"], 30)
        self.assertEqual(d["actual_value"], 30)
        self.assertTrue(d["verified"])
        self.assertFalse(d["requires_confirmation"])
        self.assertIsNone(d["error"])
        self.assertIn("Volume set to 30%", str(res))

    def test_result_contract_failure(self):
        res = SystemControlResult(
            success=False,
            action="set_brightness",
            requested_value=50,
            verified=False,
            error="WMI Unsupported"
        )
        d = res.to_dict()
        self.assertFalse(d["success"])
        self.assertFalse(d["verified"])
        self.assertEqual(d["error"], "WMI Unsupported")


class TestArgumentValidationAndUnknownSettings(unittest.TestCase):
    """Tests 2 & 3: Argument validation, unknown settings, unsupported features."""

    def test_unknown_settings_page(self):
        res = settings_uris.open_settings_page("non_existent_page_xyz")
        self.assertFalse(res.success)
        self.assertIn("Unknown settings page", res.error)

    def test_invalid_theme_mode(self):
        res = personalization.set_theme("neon_purple")
        self.assertFalse(res.success)
        self.assertIn("Mode must be 'dark' or 'light'", res.error)

    def test_invalid_projection_mode(self):
        res = display.switch_projection_mode("hologram_3d")
        self.assertFalse(res.success)
        self.assertIn("Invalid projection mode", res.error)

    def test_invalid_service_control_action(self):
        res = system.service_control("wuauserv", "explode")
        self.assertFalse(res.success)

    def test_wallpaper_non_existent_path(self):
        res = personalization.set_wallpaper("C:\\fake_non_existent_image.png")
        self.assertFalse(res.success)
        self.assertIn("does not exist", res.error)


class TestRunnerSafeguardsAndTimeouts(unittest.TestCase):
    """Tests 4 & 5: Sanitization and command timeouts."""

    def test_output_sanitization(self):
        raw = "Connecting to SSID: OfficeNetwork Key Content : MySecretPassword123\nToken = abcd_token"
        sanitized = runner.sanitize_output(raw)
        self.assertNotIn("MySecretPassword123", sanitized)
        self.assertIn("[PROTECTED]", sanitized)

    @patch("subprocess.run")
    def test_command_timeout_handling(self, mock_run):
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired(cmd=["test"], timeout=1.0)
        rc, out, err = runner.run_cmd(["test"], timeout=1.0)
        self.assertEqual(rc, -1)
        self.assertIn("timed out", err)


class TestAudioControls(unittest.TestCase):
    """Test Audio capabilities with live read-only checks or mocked hardware calls."""

    def test_get_volume_live(self):
        if platform.system() != "Windows":
            self.skipTest("Windows-only test")
        res = audio.get_volume()
        self.assertTrue(res.success)
        self.assertIsInstance(res.actual_value, int)
        self.assertTrue(0 <= res.actual_value <= 100)
        self.assertTrue(res.verified)

    def test_get_mute_state_live(self):
        if platform.system() != "Windows":
            self.skipTest("Windows-only test")
        res = audio.get_mute_state()
        self.assertTrue(res.success)
        self.assertIsInstance(res.actual_value, bool)

    def test_list_audio_devices_live(self):
        if platform.system() != "Windows":
            self.skipTest("Windows-only test")
        res = audio.list_audio_devices()
        self.assertTrue(res.success)
        self.assertIn("outputs", res.details)
        self.assertIn("inputs", res.details)

    @patch("core.windows_control.audio._get_master_endpoint")
    def test_set_volume_mocked_verified(self, mock_endpoint):
        mock_vol = MagicMock()
        mock_vol.GetMasterVolumeLevel.return_value = -10.0  # ~31%
        mock_endpoint.return_value = mock_vol
        res = audio.set_volume(30)
        self.assertTrue(res.success)
        mock_vol.SetMasterVolumeLevel.assert_called_once()

    @patch("core.windows_control.audio._get_master_endpoint")
    def test_set_mute_mocked(self, mock_endpoint):
        mock_vol = MagicMock()
        mock_vol.GetMute.return_value = 1
        mock_endpoint.return_value = mock_vol
        res = audio.set_mute(True)
        self.assertTrue(res.success)
        mock_vol.SetMute.assert_called_with(1, None)


class TestDisplayAndPersonalization(unittest.TestCase):
    """Test Display, Brightness & Theme preferences."""

    def test_get_theme_status_live(self):
        if platform.system() != "Windows":
            self.skipTest("Windows-only test")
        res = personalization.get_theme_status()
        self.assertTrue(res.success)
        self.assertIn(res.details.get("app_theme"), ("Light", "Dark"))
        self.assertIn(res.details.get("system_theme"), ("Light", "Dark"))

    def test_enumerate_displays_live(self):
        if platform.system() != "Windows":
            self.skipTest("Windows-only test")
        res = display.enumerate_displays()
        self.assertTrue(res.success)
        self.assertTrue(len(res.details.get("displays", [])) >= 1)

    def test_get_gpu_info_live(self):
        if platform.system() != "Windows":
            self.skipTest("Windows-only test")
        res = display.get_gpu_info()
        self.assertTrue(res.success)
        self.assertTrue(len(res.details.get("gpus", [])) >= 1)


class TestNetworkSafeguardsAndDiagnostics(unittest.TestCase):
    """Test Network Diagnostics and Active Connection Safeguards."""

    def test_network_diagnostics_live(self):
        res = network.run_network_diagnostics()
        self.assertIn("dns", res.details)
        self.assertIn("gateway", res.details)
        self.assertIn("internet", res.details)
        self.assertTrue(res.verified)

    @patch("core.windows_control.network.is_active_session_adapter")
    def test_disconnect_wifi_active_session_safeguard(self, mock_is_active):
        mock_is_active.return_value = True
        with patch("core.windows_control.network.get_wifi_status") as mock_status:
            mock_status.return_value = SystemControlResult(
                success=True, action="get_wifi_status",
                details={"connected": True, "ssid": "OfficeNet"}
            )
            res = network.disconnect_wifi()
            self.assertFalse(res.success)
            self.assertTrue(res.requires_confirmation)
            self.assertIn("Active session safeguard", res.error)

    @patch("core.windows_control.network.is_active_session_adapter")
    def test_disable_wifi_active_session_safeguard(self, mock_is_active):
        mock_is_active.return_value = True
        res = network.set_wifi_state(False)
        self.assertFalse(res.success)
        self.assertTrue(res.requires_confirmation)


class TestPowerAndBattery(unittest.TestCase):
    """Test Battery, Power Status, and Power Schemes."""

    def test_get_power_status_live(self):
        if platform.system() != "Windows":
            self.skipTest("Windows-only test")
        res = power.get_power_status()
        self.assertTrue(res.success)
        self.assertIn("ac", res.details)

    def test_get_power_plans_live(self):
        if platform.system() != "Windows":
            self.skipTest("Windows-only test")
        res = power.get_power_plans()
        self.assertTrue(res.success)
        self.assertIsNotNone(res.details.get("active_plan"))


class TestSecurityServicesAndStorageSafeguards(unittest.TestCase):
    """Test Security, Service Blacklist, Storage Dry-run."""

    def test_get_elevation_status_live(self):
        res = system.get_elevation_status()
        self.assertTrue(res.success)
        self.assertIsInstance(res.actual_value, bool)

    def test_get_security_status_live(self):
        if platform.system() != "Windows":
            self.skipTest("Windows-only test")
        res = system.get_security_status()
        self.assertTrue(res.success)
        self.assertIn("Antivirus", res.details)

    def test_protected_service_blacklist(self):
        """Ensure critical Windows services cannot be stopped or restarted."""
        for svc in ("rpcss", "dcomlaunch", "winmgmt", "lsass"):
            res = system.service_control(svc, "stop")
            self.assertFalse(res.success)
            self.assertIn("is protected and critical", res.error)

    def test_protected_process_blacklist(self):
        """Ensure critical Windows processes cannot be closed."""
        for proc in ("explorer.exe", "svchost.exe", "dwm.exe", "services.exe"):
            res = system.close_application_gracefully(proc)
            self.assertFalse(res.success)
            self.assertIn("critical Windows system process", res.message)

    def test_preview_temp_cleanup_dry_run(self):
        """Verify dry-run temp preview does NOT delete files."""
        res = system.preview_temp_cleanup()
        self.assertTrue(res.success)
        self.assertIn("No files were removed", res.message)
        self.assertTrue(res.details["size_mb"] >= 0)

    def test_get_disk_usage_live(self):
        res = system.get_disk_usage()
        self.assertTrue(res.success)
        self.assertTrue(len(res.details.get("drives", [])) >= 1)

    def test_get_windows_version_live(self):
        if platform.system() != "Windows":
            self.skipTest("Windows-only test")
        res = system.get_windows_version()
        self.assertTrue(res.success)
        self.assertIn("build", res.details)


class TestEDITHSecurityClassification(unittest.TestCase):
    """Test EDITH risk classification rules."""

    def test_level_3_restricted_to_shutdown_restart_delete(self):
        from core import edith
        # Level 3 actions
        lvl, _ = edith.evaluate("computer_settings", {"action": "shutdown"})
        self.assertEqual(lvl, 3)
        lvl, _ = edith.evaluate("computer_settings", {"action": "restart"})
        self.assertEqual(lvl, 3)
        lvl, _ = edith.evaluate("file_controller", {"action": "delete"})
        self.assertEqual(lvl, 3)
        lvl, _ = edith.evaluate("laptop_control", {"action": "empty_recycle_bin"})
        self.assertEqual(lvl, 3)

        # Non-Level 3 actions (must NOT require confirmation)
        lvl, _ = edith.evaluate("computer_settings", {"action": "volume_up"})
        self.assertNotEqual(lvl, 3)
        lvl, _ = edith.evaluate("laptop_control", {"action": "wifi_status"})
        self.assertEqual(lvl, 0)
        lvl, _ = edith.evaluate("laptop_control", {"action": "set_volume", "value": "50"})
        self.assertEqual(lvl, 1)
        lvl, _ = edith.evaluate("laptop_control", {"action": "network_diagnostics"})
        self.assertEqual(lvl, 0)


if __name__ == "__main__":
    unittest.main()
