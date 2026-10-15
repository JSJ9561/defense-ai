import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from agent.collector import collect_file
from unittest.mock import patch
from agent.collector import follow_file

# 보안 로그 파일 수집 테스트
class TestCollector(unittest.TestCase):
    def test_collect_mixed_logs(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'secure.log'
            logs = 'Oct 14 22:47:50 defense-rocky sshd-session[4371]: Failed password for secadmin from 192.0.2.10 port 52723 ssh2\nOct 14 22:47:54 defense-rocky sshd-session[4371]: Accepted password for secadmin from 192.0.2.10 port 52723 ssh2'
            path.write_text(logs, encoding='utf-8')

            events = collect_file(path=str(path),
                                  year=2026,
                                  agent_id='rocky-agent-01',
                                  host_id='rocky-vm-01'
            )

            self.assertEqual(len(events), 1)
            self.assertEqual(events[0].attributes['username'], 'secadmin')
            self.assertEqual(events[0].attributes["source_ip"], "192.0.2.10")
            self.assertEqual(events[0].occurred_at, "2026-10-14T13:47:50Z")

    # 빈 로그 파일 수집 테스트
    def test_empty_file(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'secure_log'
            logs = ''
            path.write_text(logs, encoding='utf-8')

            events = collect_file(path=str(path),
                                  year=2026,
                                  agent_id='rocky-agent-01',
                                  host_id='rocky-vm-01'
            )

            self.assertEqual(events, [])

# 실시간 로그 수집 테스트
class TestFollowFile(unittest.TestCase):
    def test_follow_new_line(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'secure_log'
            logs = 'Oct 14 22:47:50 defense-rocky sshd-session[4371]: Failed password for olduser from 192.0.2.10 port 52723 ssh2\n'
            path.write_text(logs, encoding='utf-8')

            appended = False
            # 대기 시 새 로그 추가 코드
            def append_new_line(seconds):
                nonlocal appended
                if appended:
                    self.fail('새 로그가 이벤트로 반환되지 않았습니다.')
                appended = True

                with open(path, 'a', encoding='utf-8') as log_file:
                    logs = 'Oct 14 22:47:50 defense-rocky sshd-session[4371]: Failed password for newuser from 192.0.2.10 port 52723 ssh2\n'
                    log_file.write(logs)

            # 대기 함수를 교체해 새 로그 수집 검증 코드
            with patch('agent.collector.sleep', side_effect=append_new_line):
                stream = follow_file(path=str(path),
                                     year=2026,
                                     agent_id='rocky-agent-01',
                                     host_id='rocky-vm-01'
                )

                try:
                    event = next(stream)
                    self.assertEqual(event.attributes['username'], 'newuser')
                finally:
                    stream.close()

    # 미완성 로그 대기 검증 함수
    def test_follow_partial_line(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'secure_log'
            path.write_text('', encoding='utf-8')

            wait_count = 0
            def append_new_line(seconds):
                nonlocal wait_count
                wait_count += 1
                with open(path, 'a', encoding='utf-8') as log_file:
                    if wait_count == 1:
                        logs = 'Oct 14 22:47:50 defense-rocky sshd-session[4371]: Failed password for newuser from 192.0.2.10 port 52723 ssh2'
                        log_file.write(logs)
                    elif wait_count == 2:
                        log_file.write('\n')
                    else:
                        self.fail('완성된 로그가 이벤트로 반환되지 않았습니다.')

            with patch('agent.collector.sleep', side_effect=append_new_line):
                stream = follow_file(path=str(path),
                                     year=2026,
                                     agent_id='rocky-agent-01',
                                     host_id='rocky-vm-01'
                )

                try:
                    event = next(stream)
                    self.assertEqual(wait_count, 2)
                    self.assertEqual(event.attributes['username'], 'newuser')
                finally:
                    stream.close()
