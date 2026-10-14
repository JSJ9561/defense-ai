import unittest
from agent.ssh_parser import parse_ssh_login_failed, parse_log_timestamp, parse_ssh_event

# ssh 로그인 실패 로그 파싱 테스트
class TestSSHParser(unittest.TestCase):
    def test_valid_user(self):
        line = 'Oct 13 22:29:02 defense-rocky sshd-session[3529]: Failed password for secadmin from 192.0.2.10 port 57866 ssh2'

        result = parse_ssh_login_failed(line)

        self.assertEqual(result, {'username': 'secadmin', 'source_ip': '192.0.2.10'})

    def test_invalid_user(self):
        line = 'Oct 13 22:29:02 defense-rocky sshd-session[3529]: Failed password for invalid user unknown from 192.0.2.10 port 57866 ssh2'

        result = parse_ssh_login_failed(line)

        self.assertEqual(result, {'username': 'unknown', 'source_ip': '192.0.2.10'})

    def test_invalid_ip(self):
        line = 'Oct 13 22:29:02 defense-rocky sshd-session[3529]: Failed password for invalid user unknown from abc port 57866 ssh2'

        result = parse_ssh_login_failed(line)

        self.assertIsNone(result)

    def test_invalid_port(self):
        line = 'Oct 13 22:29:02 defense-rocky sshd-session[3529]: Failed password for secadmin from 192.0.2.10 port 65536 ssh2'

        result = parse_ssh_login_failed(line)

        self.assertIsNone(result)

    def test_login_success_ignored(self):
        line = 'Oct 13 22:29:02 defense-rocky sshd-session[3529]: Accepted password for secadmin from 192.0.2.10 port 57866 ssh2'

        result = parse_ssh_login_failed(line)

        self.assertIsNone(result)

    def test_short_message(self):
        line = 'Oct 13 22:29:02 defense-rocky sshd-session[3529]: Failed password for secadmin'

        result = parse_ssh_login_failed(line)

        self.assertIsNone(result)

    def test_wrong_separator(self):
        line = 'Oct 13 22:29:02 defense-rocky sshd-session[3529]: Failed password for secadmin wrong 192.0.2.10 port 57866 ssh2'

        result = parse_ssh_login_failed(line)

        self.assertIsNone(result)

    def test_nonnumeric_port(self):
        line = 'Oct 13 22:29:02 defense-rocky sshd-session[3529]: Failed password for secadmin from 192.0.2.10 port abc ssh2'

        result = parse_ssh_login_failed(line)

        self.assertIsNone(result)

    def test_zero_port(self):
        line = 'Oct 13 22:29:02 defense-rocky sshd-session[3529]: Failed password for secadmin from 192.0.2.10 port 0 ssh2'

        result = parse_ssh_login_failed(line)

        self.assertIsNone(result)

    def test_max_port(self):
        line = 'Oct 13 22:29:02 defense-rocky sshd-session[3529]: Failed password for secadmin from 192.0.2.10 port 65535 ssh2'

        result = parse_ssh_login_failed(line)

        self.assertEqual(result, {'username': 'secadmin', 'source_ip': '192.0.2.10'})

    def test_ipv6(self):
        line = 'Oct 13 22:29:02 defense-rocky sshd-session[3529]: Failed password for secadmin from 2001:db8::10 port 57866 ssh2'

        result = parse_ssh_login_failed(line)

        self.assertEqual(result, {'username': 'secadmin', 'source_ip': '2001:db8::10'})

# 로그 타임스탬프 변환 테스트
class TestLogTimestamp(unittest.TestCase):
    def test_kst_to_utc(self):
        line = 'Oct 13 22:29:02'
        year = 2026

        result = parse_log_timestamp(line, year)

        self.assertEqual(result, '2026-10-13T13:29:02Z')

    def test_year_boundary(self):
        line = 'Jan 1 00:30:00'
        year = 2026

        result = parse_log_timestamp(line, year)

        self.assertEqual(result, '2025-12-31T15:30:00Z')

    def test_invalid_date(self):
        line = 'Feb 30 12:00:00'
        year = 2026

        result = parse_log_timestamp(line, year)

        self.assertIsNone(result)

    def test_invalid_time(self):
        line = 'Oct 13 25:00:00'
        year = 2026

        result = parse_log_timestamp(line, year)

        self.assertIsNone(result)

    def test_nonnumeric_time(self):
        line = 'Oct 13 aa:29:02'
        year = 2026

        result = parse_log_timestamp(line, year)

        self.assertIsNone(result)

    def test_unknown_month(self):
        line = 'Abc 13 22:29:02'
        year = 2026

        result = parse_log_timestamp(line, year)

        self.assertIsNone(result)

    def test_short_timestamp(self):
        line = 'Oct 13'
        year = 2026

        result = parse_log_timestamp(line, year)

        self.assertIsNone(result)

# ssh 로그의 보안 이벤트 변환 테스트
class TestSSHEvent(unittest.TestCase):
    def test_create_event(self):
        line = 'Oct 13 22:29:02 defense-rocky sshd-session[3529]: Failed password for secadmin from 192.0.2.10 port 57866 ssh2'
        year = 2026

        event = parse_ssh_event(
            line,
            year,
            agent_id='rocky-agent-01',
            host_id='rocky-vm-01'
        )

        self.assertIsNotNone(event)
        self.assertEqual(event.event_type, "auth.login_failed")
        self.assertEqual(event.occurred_at, "2026-10-13T13:29:02Z")
        self.assertEqual(event.agent_id, 'rocky-agent-01')
        self.assertEqual(event.host_id, 'rocky-vm-01')
        self.assertEqual(
            dict(event.attributes),
            {
                "service": "sshd",
                "username": "secadmin",
                "source_ip": "192.0.2.10"
            }
        )

    def test_login_success_ignored(self):
        line = 'Oct 13 22:29:02 defense-rocky sshd-session[3529]: Accepted password for secadmin from 192.0.2.10 port 57866 ssh2'
        year = 2026

        event = parse_ssh_event(
            line,
            year,
            agent_id='rocky-agent-01',
            host_id='rocky-vm-01'
        )

        self.assertIsNone(event)

    def test_invalid_timestamp(self):
        line = 'Feb 30 22:29:02 defense-rocky sshd-session[3529]: Failed password for secadmin from 192.0.2.10 port 57866 ssh2'
        year = 2026

        event = parse_ssh_event(
            line,
            year,
            agent_id='rocky-agent-01',
            host_id='rocky-vm-01'
        )

        self.assertIsNone(event)
