import unittest
from tempfile import TemporaryDirectory
from pathlib import Path
from agent.buffer import initialize_buffer, count_events, peek_events, enqueue_event, acknowledge_event
from common.event import SecurityEvent
import sqlite3

# 이벤트 버퍼 테스트
class TestBuffer(unittest.TestCase):
    # 빈 이벤트 버퍼 초기화 검증 함수
    def test_initialize_empty_buffer(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'db'

            initialize_buffer(db_path=str(path))
            self.assertEqual(count_events(str(path)), 0)

            initialize_buffer(db_path=str(path))
            self.assertEqual(count_events(str(path)), 0)

    # 이벤트 버퍼 추가 및 조회 검증 함수
    def test_enqueue_and_peek_event(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'db'
            initialize_buffer(db_path=str(path))
            event = SecurityEvent.create_login_failure(
                agent_id='rocky-agent-01',
                host_id='rocky-vm-01',
                service='sshd',
                username='user'
            )

            enqueue_event(db_path=str(path), event=event)
            count = count_events(db_path=str(path))
            peek = peek_events(db_path=str(path), limit=10)

            self.assertEqual(count, 1)
            self.assertEqual(peek, [event])
            self.assertEqual(count_events(db_path=str(path)), 1)

    # 저장 순서와 조회 개수 제한 함수
    def test_peek_order_and_limit(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'db'
            initialize_buffer(db_path=str(path))
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
            event3 = SecurityEvent.create_login_failure(
                agent_id='rocky-agent-01',
                host_id='rocky-vm-01',
                service='sshd',
                username='user3'
            )

            enqueue_event(db_path=str(path), event=event1)
            enqueue_event(db_path=str(path), event=event2)
            enqueue_event(db_path=str(path), event=event3)

            peek2 = peek_events(db_path=str(path), limit=2)
            self.assertEqual(peek2, [event1, event2])

            peek10 = peek_events(db_path=str(path), limit=10)
            self.assertEqual(peek10, [event1, event2, event3])

            self.assertEqual(count_events(db_path=str(path)), 3)

    # 전송 완료 이벤트 삭제 검증 함수
    def test_acknowledge_event(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'db'
            initialize_buffer(db_path=str(path))
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

            enqueue_event(db_path=str(path), event=event1)
            enqueue_event(db_path=str(path), event=event2)

            acknowledge_event(db_path=str(path), event_id=event1.event_id)
            self.assertEqual(peek_events(db_path=str(path), limit=1), [event2])
            self.assertEqual(count_events(db_path=str(path)), 1)

            acknowledge_event(db_path=str(path), event_id=event1.event_id)
            self.assertEqual(peek_events(db_path=str(path), limit=1), [event2])
            self.assertEqual(count_events(db_path=str(path)), 1)

    # 중복 이벤트 삽입 방지 테스트
    def test_duplicate_event_rejected(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'db'
            initialize_buffer(db_path=str(path))
            event = SecurityEvent.create_login_failure(
                agent_id='rocky-agent-01',
                host_id='rocky-vm-01',
                service='sshd',
                username='user'
            )

            enqueue_event(db_path=str(path), event=event)

            with self.assertRaises(sqlite3.IntegrityError):
                enqueue_event(db_path=str(path), event=event)

            count = count_events(db_path=str(path))
            peek = peek_events(db_path=str(path), limit=10)

            self.assertEqual(count, 1)
            self.assertEqual(peek, [event])

    # 조회 개수 자료형 검증 함수
    def test_peek_invalid_limit_type(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'db'
            initialize_buffer(db_path=str(path))
            event = SecurityEvent.create_login_failure(
                agent_id='rocky-agent-01',
                host_id='rocky-vm-01',
                service='sshd',
                username='user'
            )

            enqueue_event(db_path=str(path), event=event)

            limit_input = ['2', 2.5, True, False, None]
            for i in limit_input:
                with self.subTest(limit=i):
                    with self.assertRaises(TypeError):
                        peek_events(db_path=str(path), limit=i)

    # 조회 개수 양수 검증 함수
    def test_peek_nonpositive_limit(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'db'
            initialize_buffer(db_path=str(path))
            event = SecurityEvent.create_login_failure(
                agent_id='rocky-agent-01',
                host_id='rocky-vm-01',
                service='sshd',
                username='user'
            )

            enqueue_event(db_path=str(path), event=event)

            limit_input = [0, -1]
            for i in limit_input:
                with self.subTest(limit=i):
                    with self.assertRaises(ValueError):
                        peek_events(db_path=str(path), limit=i)

    # 버퍼 재초기화시 이벤트 유지 검증 함수
    def test_reinitialize_preserves_events(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'db'
            initialize_buffer(db_path=str(path))
            event = SecurityEvent.create_login_failure(
                agent_id='rocky-agent-01',
                host_id='rocky-vm-01',
                service='sshd',
                username='user'
            )

            enqueue_event(db_path=str(path), event=event)

            initialize_buffer(db_path=str(path))

            self.assertEqual(count_events(db_path=str(path)), 1)
            self.assertEqual(peek_events(db_path=str(path), limit=10), [event])
