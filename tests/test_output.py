import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from common.event import SecurityEvent
from agent.output import append_event_jsonl

# JSONL 이벤트 저장 테스트
class TestJsonlOutput(unittest.TestCase):
    def test_append_events(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'events.jsonl'
            event1 = SecurityEvent.create_login_failure(
                agent_id='rocky-agent-01',
                host_id='rocky-vm-01',
                service='sshd',
                username='user1'
            )

            event2 = SecurityEvent.create_login_failure(
                agent_id='rocky-agent-01',
                host_id='rocky-vm-01',
                service='sshd',
                username='user2'
            )

            append_event_jsonl(path=str(path), event=event1)
            append_event_jsonl(path=str(path), event=event2)

            lines = path.read_text(encoding='utf-8').splitlines()

            self.assertEqual(len(lines), 2)
            self.assertEqual(SecurityEvent.from_json(lines[0]), event1)
            self.assertEqual(SecurityEvent.from_json(lines[1]), event2)
