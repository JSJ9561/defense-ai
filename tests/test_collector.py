import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from agent.collector import collect_file

# 보안 로그 파일 수집 테스트
class TestCollector(unittest.TestCase):
    def test_collect_mixed_logs(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'secure.log'
            logs = 'Oct 14 22:47:50 defense-rocky sshd-session[4371]: Failed password for secadmin from 192.0.2.10 port 52723 ssh2\nOct 14 22:47:54 defense-rocky sshd-session[4371]: Accepted password for secadmin from 192.0.2.10 port 52723 ssh2'
            path.write_text(logs, encoding='utf-8')

            events = collect_file(path=str(path), year=2026, agent_id='rocky-agent-01', host_id='rocky-vm-01')

            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].attributes['username'], 'secadmin')
            self.assertEqual(events[0].attributes["source_ip"], "192.0.2.10")
            self.assertEqual(events[0].occurred_at, "2026-10-14T13:47:50Z")

    # 빈 로그 파일 수집 테스트
    def test_empty_file(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'test_empty_file'
            logs = ''
            path.write_text(logs, encoding='utf-8')

            events = collect_file(path=str(path), year=2026, agent_id='rocky-agent-01', host_id='rocky-vm-01')

            self.assertEqual(events, [])
