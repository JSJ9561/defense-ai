import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from agent.collector import collect_file
from unittest.mock import patch
from agent.collector import follow_file
from datetime import datetime, timedelta, timezone

# 보안 로그 파일 수집 테스트
class TestCollector(unittest.TestCase):
    # 여러 줄의 로그 수집 함수
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

    # 빈 로그 파일 수집 테스트 함수
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
        tzinfo = timezone(timedelta(hours=9))
        fixed_now = datetime(2027, 10, 14, 22, 48, 0, tzinfo=tzinfo)

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'secure_log'
            logs = 'Oct 14 22:47:50 defense-rocky sshd-session[4371]: Failed password for olduser from 192.0.2.10 port 52723 ssh2\n'
            path.write_text(logs, encoding='utf-8')

            appended = False

            # 대기 시 새 로그 추가 함수
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
                # 현재 시각 고정 코드
                with patch('agent.collector.datetime') as mock_datetime:
                    mock_datetime.now.return_value = fixed_now

                    stream = follow_file(path=str(path),
                                         agent_id='rocky-agent-01',
                                         host_id='rocky-vm-01'
                                        )

                    try:
                        event = next(stream)
                        self.assertEqual(event.attributes['username'], 'newuser')
                        self.assertEqual(event.occurred_at, '2027-10-14T13:47:50Z')
                    finally:
                        stream.close()

    # 연도 변경 후 수집 검증 함수
    def test_follow_year_rollover(self):
        tzinfo = timezone(timedelta(hours=9))
        before_midnight = datetime(2026, 12, 31, 23, 59, 59, tzinfo=tzinfo)
        after_midnight = datetime(2027, 1, 1, 0, 0, 1, tzinfo=tzinfo)

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'secure_log'
            logs = 'Oct 14 22:47:50 defense-rocky sshd-session[4371]: Failed password for secadmin from 192.0.2.10 port 52723 ssh2\n'
            path.write_text(logs, encoding='utf-8')

            wait_count = 0

            # 대기 시 연말과 연초 로그 추가 함수
            def year_change_log(seconds):
                nonlocal wait_count
                wait_count += 1
                with open(path, 'a', encoding='utf-8') as log_file:
                    if wait_count == 1:
                        logs = 'Dec 31 23:59:59 defense-rocky sshd-session[4371]: Failed password for newuser from 192.0.2.10 port 52723 ssh2\n'
                        log_file.write(logs)
                    elif wait_count == 2:
                        logs = 'Jan 1 00:00:01 defense-rocky sshd-session[4371]: Failed password for newuser from 192.0.2.10 port 52723 ssh2\n'
                        log_file.write(logs)
                    else:
                        self.fail('연도 변경 후 로그가 반환되지 않았습니다.')

            with patch('agent.collector.sleep', side_effect=year_change_log):
                with patch('agent.collector.datetime') as mock_datetime:
                    mock_datetime.now.side_effect = [before_midnight, after_midnight]
                    stream = follow_file(path=str(path),
                                         agent_id='rocky-agent-01',
                                         host_id='rocky-vm-01'
                                         )

                    try:
                        event1 = next(stream)
                        event2 = next(stream)
                        self.assertEqual(event1.occurred_at, '2026-12-31T14:59:59Z')
                        self.assertEqual(event2.occurred_at, '2026-12-31T15:00:01Z')
                        self.assertEqual(wait_count, 2)
                    finally:
                        stream.close()

    # 지연된 연말 로그 수집 검증 함수
    def test_follow_delayed_year_end_line(self):
        tzinfo = timezone(timedelta(hours=9))
        fixed_now = datetime(2027, 1, 1, 0, 0, 1, tzinfo=tzinfo)

        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'secure_log'
            logs = ''
            path.write_text(logs, encoding='utf-8')

            appended = False

            # 대기 시 새 로그 추가 함수
            def append_new_line(seconds):
                nonlocal appended
                if appended:
                    self.fail('새 로그가 이벤트로 반환되지 않았습니다.')
                appended = True

                with open(path, 'a', encoding='utf-8') as log_file:
                    logs = 'Dec 31 23:59:59 defense-rocky sshd-session[4371]: Failed password for newuser from 192.0.2.10 port 52723 ssh2\n'
                    log_file.write(logs)

            with patch('agent.collector.sleep', side_effect=append_new_line):
                with patch('agent.collector.datetime') as mock_time:
                    mock_time.now.return_value = fixed_now
                    stream = follow_file(path=str(path),
                                         agent_id='rocky-agent-01',
                                         host_id='rocky-vm-01'
                                         )

                    try:
                        event = next(stream)
                        self.assertEqual(event.occurred_at, '2026-12-31T14:59:59Z')
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
                                     agent_id='rocky-agent-01',
                                     host_id='rocky-vm-01'
                                    )

                try:
                    event = next(stream)
                    self.assertEqual(wait_count, 2)
                    self.assertEqual(event.attributes['username'], 'newuser')
                finally:
                    stream.close()

    # 파일 잘림 후 수집 검증 함수
    def test_follow_truncated_file(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'secure_log'
            logs = 'Oct 14 22:47:50 defense-rocky sshd-session[4371]: Failed password for olduser from 192.0.2.10 port 52723 ssh2\n'
            path.write_text(logs, encoding='utf-8')

            wait_count = 0

            # 대기 시 파일 잘림과 새 로그 기록 함수
            def truncate_and_append(seconds):
                nonlocal wait_count
                wait_count += 1
                if wait_count == 1:
                    path.write_text('', encoding='utf-8')
                elif wait_count == 2:
                    with open(path, 'a', encoding='utf-8') as log_file:
                        logs = 'Oct 14 22:47:50 defense-rocky sshd-session[4371]: Failed password for newuser from 192.0.2.10 port 52723 ssh2\n'
                        log_file.write(logs)
                else:
                    self.fail('파일 잘림 후 새 로그가 반환되지 않았습니다.')

            with patch('agent.collector.sleep', side_effect=truncate_and_append):
                stream = follow_file(path=str(path),
                                     agent_id='rocky-agent-01',
                                     host_id='rocky-vm-01'
                                    )

                try:
                    event = next(stream)
                    self.assertEqual(wait_count, 2)
                    self.assertEqual(event.attributes['username'], 'newuser')
                finally:
                    stream.close()

    # 파일 교체 후 수집 검증 함수
    def test_follow_replaced_file(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'secure_log'
            rotated_path = Path(temp_dir) / 'secure_log.1'
            logs = 'Oct 14 22:47:50 defense-rocky sshd-session[4371]: Failed password for olduser from 192.0.2.10 port 52723 ssh2\n'
            path.write_text(logs, encoding='utf-8')

            wait_count = 0

            # 대기 시 기존 파일 이동과 새 파일 생성 함수
            def replace_file(seconds):
                nonlocal wait_count
                wait_count += 1
                logs = 'Oct 14 22:47:50 defense-rocky sshd-session[4371]: Failed password for newuser from 192.0.2.10 port 52723 ssh2\n'

                if wait_count == 1:
                    path.rename(rotated_path)
                elif wait_count == 2:
                    path.write_text(logs, encoding='utf-8')
                else:
                    self.fail('파일 교체 후 새 로그가 반환되지 않았습니다.')

            with patch('agent.collector.sleep', side_effect=replace_file):
                stream = follow_file(path=str(path),
                                     agent_id='rocky-agent-01',
                                     host_id='rocky-vm-01'
                                     )

                try:
                    event = next(stream)
                    self.assertEqual(wait_count, 2)
                    self.assertEqual(event.attributes['username'], 'newuser')
                finally:
                    stream.close()
