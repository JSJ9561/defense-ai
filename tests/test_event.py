import unittest
from common.event import (
    EventValidationError,
    SecurityEvent,
)

# 보안 이벤트 데이터 검증 테스트
class TestSecurityEvent(unittest.TestCase):

    def setUp(self):
        self.event = SecurityEvent.create_login_failure(
            agent_id="rocky-agent-01",
            host_id="rocky-vm-01",
            service="sshd",
            username="example",
            source_ip="192.0.2.10",
            occurred_at="2026-10-13T06:33:59Z",
        )

    def test_create_event(self):
        self.assertEqual(self.event.schema_version, "1.0")
        self.assertEqual(
            self.event.event_type,
            "auth.login_failed"
        )
        self.assertEqual(
            self.event.attributes["service"],
            "sshd"
        )

    def test_json_roundtrip(self):
        json_text = self.event.to_json()
        restored = SecurityEvent.from_json(json_text)

        self.assertEqual(
            self.event.to_dict(),
            restored.to_dict()
        )

    def test_missing_field(self):
        data = self.event.to_dict()
        del data["agent_id"]

        with self.assertRaises(EventValidationError):
            SecurityEvent.from_dict(data)

    def test_extra_field(self):
        data = self.event.to_dict()
        data["unexpected"] = "value"

        with self.assertRaises(EventValidationError):
            SecurityEvent.from_dict(data)

    def test_invalid_uuid(self):
        data = self.event.to_dict()
        data["event_id"] = "invalid-uuid"

        with self.assertRaises(EventValidationError):
            SecurityEvent.from_dict(data)

    def test_invalid_timestamp(self):
        data = self.event.to_dict()
        data["observed_at"] = "2026-02-30T12:00:00Z"

        with self.assertRaises(EventValidationError):
            SecurityEvent.from_dict(data)

    def test_unknown_event_type(self):
        data = self.event.to_dict()
        data["event_type"] = "unknown.event"

        with self.assertRaises(EventValidationError):
            SecurityEvent.from_dict(data)

    def test_invalid_ip(self):
        data = self.event.to_dict()
        data["attributes"]["source_ip"] = "999.999.999.999"

        with self.assertRaises(EventValidationError):
            SecurityEvent.from_dict(data)

    def test_missing_service(self):
        data = self.event.to_dict()
        del data["attributes"]["service"]

        with self.assertRaises(EventValidationError):
            SecurityEvent.from_dict(data)

    def test_disallowed_attribute(self):
        data = self.event.to_dict()
        data["attributes"]["password"] = "secret"

        with self.assertRaises(EventValidationError):
            SecurityEvent.from_dict(data)

    def test_optional_fields(self):
        event = SecurityEvent.create_login_failure(
            agent_id="rocky-agent-01",
            host_id="rocky-vm-01",
            service="sshd",
        )

        self.assertIsNone(event.occurred_at)
        self.assertNotIn("username", event.attributes)
        self.assertNotIn("source_ip", event.attributes)

    def test_invalid_json(self):
        with self.assertRaises(EventValidationError):
            SecurityEvent.from_json("{invalid json}")

    def test_attributes_immutable(self):
        with self.assertRaises(TypeError):
            self.event.attributes["password"] = "secret"

    def test_attributes_defensive_copy(self):
        data = self.event.to_dict()
        restored = SecurityEvent.from_dict(data)

        data["attributes"]["service"] = "modified"

        self.assertEqual(
            restored.attributes["service"],
            "sshd"
        )

    def test_duplicate_json_field(self):
        text = self.event.to_json().replace(
            '"agent_id": "rocky-agent-01"',
            '"agent_id": "rocky-agent-01", "agent_id": "other"',
            1,
        )

        with self.assertRaises(EventValidationError):
            SecurityEvent.from_json(text)

    def test_duplicate_attribute_field(self):
        text = self.event.to_json().replace(
            '"service": "sshd"',
            '"service": "sshd", "service": "ssh"',
            1,
        )

        with self.assertRaises(EventValidationError):
            SecurityEvent.from_json(text)

if __name__ == "__main__":
    unittest.main()
