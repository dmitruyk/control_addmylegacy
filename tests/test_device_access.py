from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse

from core.device_access import device_fingerprint, stable_headers_snapshot
from core.models import AllowedDevice, DeviceAccessLog


class DeviceFingerprintTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_fingerprint_ignores_ip_headers(self):
        base = self.factory.get("/", HTTP_USER_AGENT="TestAgent/1.0", HTTP_ACCEPT_LANGUAGE="en-US")
        with_ip = self.factory.get(
            "/",
            HTTP_USER_AGENT="TestAgent/1.0",
            HTTP_ACCEPT_LANGUAGE="en-US",
            REMOTE_ADDR="203.0.113.10",
            HTTP_X_FORWARDED_FOR="203.0.113.10, 198.51.100.2",
            HTTP_X_REAL_IP="203.0.113.10",
        )

        self.assertEqual(device_fingerprint(base), device_fingerprint(with_ip))

    def test_fingerprint_changes_when_user_agent_changes(self):
        first = self.factory.get("/", HTTP_USER_AGENT="Agent-A")
        second = self.factory.get("/", HTTP_USER_AGENT="Agent-B")

        self.assertNotEqual(device_fingerprint(first), device_fingerprint(second))

    def test_stable_headers_snapshot_excludes_ip(self):
        request = self.factory.get(
            "/",
            HTTP_USER_AGENT="Phone/1.0",
            REMOTE_ADDR="10.0.0.5",
            HTTP_X_FORWARDED_FOR="10.0.0.5",
        )
        snapshot = stable_headers_snapshot(request)

        self.assertIn("USER-AGENT", snapshot)
        self.assertNotIn("REMOTE-ADDR", snapshot)
        self.assertNotIn("X-FORWARDED-FOR", snapshot)


class DeviceAccessControlTests(TestCase):
    def _allow_latest_device(self):
        device = AllowedDevice.objects.order_by("-last_seen_at").first()
        self.assertIsNotNone(device)
        device.is_allowed = True
        device.save(update_fields=["is_allowed"])
        return device

    @override_settings(
        CACHES={
            "default": {
                "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
                "LOCATION": "device-access-tests",
            }
        }
    )
    def test_new_device_is_blocked_by_default(self):
        response = self.client.get(reverse("core:tv_dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-device-widgets-allowed="false"')
        self.assertNotContains(response, "tv-wealth-card")
        self.assertNotContains(response, "tv-binance-card")
        self.assertContains(response, "Palo Alto")

        device = AllowedDevice.objects.get()
        self.assertFalse(device.is_allowed)

        log = DeviceAccessLog.objects.get(access_type="page")
        self.assertEqual(log.path, "/")
        self.assertFalse(log.is_allowed_at_access)
        self.assertContains(response, 'id="tv-widget-wealth" hidden')
        self.assertContains(response, 'id="tv-widget-binance" hidden')

    def test_restricted_widget_apis_return_403_when_blocked(self):
        wealth = self.client.get(reverse("core:tv_widget_wealth"))
        binance = self.client.get(reverse("core:tv_widget_binance"))
        weather = self.client.get(reverse("core:tv_widget_weather"))

        self.assertEqual(wealth.status_code, 403)
        self.assertEqual(binance.status_code, 403)
        self.assertEqual(weather.status_code, 200)

        self.assertEqual(
            DeviceAccessLog.objects.filter(access_type="restricted_widget").count(),
            2,
        )

    def test_allowed_device_gets_restricted_widgets(self):
        self.client.get(reverse("core:tv_dashboard"))
        self._allow_latest_device()

        response = self.client.get(reverse("core:tv_dashboard"))

        self.assertContains(response, 'data-device-widgets-allowed="true"')
        self.assertContains(response, "tv-wealth-card")
        self.assertContains(response, "tv-binance-card")

        wealth = self.client.get(reverse("core:tv_widget_wealth"))
        self.assertEqual(wealth.status_code, 200)

    def test_network_headers_are_logged_separately(self):
        self.client.get(
            reverse("core:tv_dashboard"),
            REMOTE_ADDR="192.0.2.44",
            HTTP_X_FORWARDED_FOR="192.0.2.44",
            HTTP_USER_AGENT="LivingRoomTV/2.0",
        )

        log = DeviceAccessLog.objects.latest("created_at")
        self.assertEqual(log.ip_address, "192.0.2.44")
        self.assertEqual(log.forwarded_for, "192.0.2.44")
        self.assertIn("REMOTE-ADDR", log.network_headers)
        self.assertNotIn("REMOTE-ADDR", log.stable_headers)

    def test_display_config_reports_device_access_state(self):
        blocked = self.client.get(reverse("core:tv_display_config"))
        self.assertEqual(blocked.status_code, 200)
        blocked_payload = blocked.json()
        self.assertFalse(blocked_payload["device_widgets_allowed"])
        self.assertEqual(blocked_payload["wealth_poll_seconds"], 0)
        self.assertEqual(blocked_payload["binance_poll_seconds"], 0)

        self.client.get(reverse("core:tv_dashboard"))
        self._allow_latest_device()

        allowed = self.client.get(reverse("core:tv_display_config"))
        allowed_payload = allowed.json()
        self.assertTrue(allowed_payload["device_widgets_allowed"])
        self.assertGreater(allowed_payload["wealth_poll_seconds"], 0)
