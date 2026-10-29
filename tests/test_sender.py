import unittest
import json
from unittest.mock import patch, MagicMock, call
from common.event import SecurityEvent
from agent.sender import send_event, send_buffered_events
from agent.buffer import initialize_buffer, enqueue_event, count_events, peek_events
from tempfile import TemporaryDirectory
from pathlib import Path

# 이벤트 전송 테스트
class TestSender(unittest.TestCase):
    # 전송 테스트 준비 함수
    def setUp(self):
        self.event = SecurityEvent.create_login_failure(
            agent_id='rocky-agent-01',
            host_id='rocky-vm-01',
            service='sshd'
        )

        self.connection = MagicMock()
        self.response = MagicMock()
        self.response.status = 201
        self.connection.getresponse.return_value = self.response

        response_data = {
            'event_id': self.event.event_id,
            'status': 'stored'
        }
        self.response.read.return_value = json.dumps(response_data).encode('utf-8')

        self.patcher = patch('agent.sender.HTTPConnection', return_value=self.connection)
        self.addCleanup(self.patcher.stop)
        self.mock_http = self.patcher.start()

    # 신규 이벤트 전송 검증 함수
    def test_send_event_created(self):
        result = send_event(
            host='127.0.0.1',
            port=8000,
            event=self.event
        )
        self.assertIsNone(result)

        self.connection.close.assert_called_once_with()

    def test_send_event_duplicate(self):
        self.response.status = 200
        result = send_event(
            host='127.0.0.1',
            port=8000,
            event=self.event
        )
        self.assertIsNone(result)

        self.connection.close.assert_called_once_with()

    # 서버 오류 응답 검증 함수
    def test_send_event_rejects_http_error(self):
        self.response.status = 500
        with self.assertRaises(RuntimeError):
            send_event(
                host='127.0.0.1',
                port=8000,
                event=self.event
            )

        self.connection.close.assert_called_once_with()

    # 응답 이벤트 ID 불일치 검증 함수
    def test_send_event_rejects_mismatched_id(self):
        response_data = {
            'event_id': 'different-id',
            'status': 'stored'
        }
        self.response.read.return_value = json.dumps(response_data).encode('utf-8')

        with self.assertRaises(RuntimeError):
            send_event(
                host='127.0.0.1',
                port=8000,
                event=self.event
            )

        self.connection.close.assert_called_once_with()

    # 응답 저장 상태 검증 함수
    def test_send_event_rejects_invalid_status(self):
        response_data = {
            'event_id': self.event.event_id,
            'status': 'failed'
        }
        self.response.read.return_value = json.dumps(response_data).encode('utf-8')

        with self.assertRaises(RuntimeError):
            send_event(
                host='127.0.0.1',
                port=8000,
                event=self.event
            )

        self.connection.close.assert_called_once_with()

    # 잘못된 응답 JSON 검증 함수
    def test_send_event_rejects_invalid_json(self):
        self.response.read.return_value = b'{'
        with self.assertRaises(json.JSONDecodeError):
            send_event(
                host='127.0.0.1',
                port=8000,
                event=self.event
            )

        self.connection.close.assert_called_once_with()

    # 연결 실패 검증 함수
    def test_send_connection_error(self):
        self.connection.request.side_effect = OSError('연결실패')
        with self.assertRaises(OSError):
            send_event(
                host='127.0.0.1',
                port=8000,
                event=self.event
            )

        self.connection.close.assert_called_once_with()

    # 응답 시간 초과 검증 함수
    def test_send_event_timeout(self):
        self.connection.getresponse.side_effect = TimeoutError('응답 시간 초과')
        with self.assertRaises(TimeoutError):
            send_event(
                host='127.0.0.1',
                port=8000,
                event=self.event
            )

        self.connection.close.assert_called_once_with()

    # 응답 객체 형식 검증 함수
    def test_send_event_rejects_non_object_response(self):
        self.response.read.return_value = b'[]'
        with self.assertRaises(RuntimeError):
            send_event(
                host='127.0.0.1',
                port=8000,
                event=self.event
            )

        self.connection.close.assert_called_once_with()

# 버퍼 이벤트 전송 테스트
class TestBufferedSender(unittest.TestCase):
    # 버퍼 전송 테스트 준비 함수
    def setUp(self):
        self.temp_dir = TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.db_path = str(Path(self.temp_dir.name) / 'buffer.db')
        initialize_buffer(db_path=self.db_path)

        self.patcher = patch('agent.sender.send_event', return_value=None)
        self.addCleanup(self.patcher.stop)
        self.mock_send = self.patcher.start()

    # 빈 버퍼 전송 검증 함수
    def test_send_empty_buffer(self):
        result = send_buffered_events(
            db_path=self.db_path,
            host='127.0.0.1',
            port=8000,
            limit=10
        )
        self.assertEqual(result, 0)

        self.mock_send.assert_not_called()

    # 전송 성공 이벤트 삭제 검증 함수
    def test_send_removes_successful_event(self):
        event = SecurityEvent.create_login_failure(
            agent_id='rocky-agent-01',
            host_id='rocky-vm-01',
            service='sshd'
        )
        enqueue_event(db_path=self.db_path, event=event)

        result = send_buffered_events(
            db_path=self.db_path,
            host='127.0.0.1',
            port=8000,
            limit=10
        )
        self.assertEqual(result, 1)
        self.assertEqual(count_events(db_path=self.db_path), 0)

        self.mock_send.assert_called_once_with(
            host='127.0.0.1',
            port=8000,
            event=event,
            timeout=5.0
        )

    # 전송 실패 이벤트 유지 검증 함수
    def test_send_preserves_failed_event(self):
        event = SecurityEvent.create_login_failure(
            agent_id='rocky-agent-01',
            host_id='rocky-vm-01',
            service='sshd'
        )
        enqueue_event(db_path=self.db_path, event=event)

        self.mock_send.side_effect = OSError('전송 실패')
        with self.assertRaises(OSError):
            send_buffered_events(
                db_path=self.db_path,
                host='127.0.0.1',
                port=8000,
                limit=10
            )

        self.assertEqual(count_events(db_path=self.db_path), 1)

        self.mock_send.assert_called_once_with(
            host='127.0.0.1',
            port=8000,
            event=event,
            timeout=5.0
        )

    # 버퍼 전송 순서 및 개수 제한 검증 함수
    def test_send_respects_order_and_limit(self):
        event1 = SecurityEvent.create_login_failure(
            agent_id='rocky-agent-01',
            host_id='rocky-vm-01',
            service='sshd'
        )
        enqueue_event(db_path=self.db_path, event=event1)

        event2 = SecurityEvent.create_login_failure(
            agent_id='rocky-agent-01',
            host_id='rocky-vm-01',
            service='sshd'
        )
        enqueue_event(db_path=self.db_path, event=event2)

        event3 = SecurityEvent.create_login_failure(
            agent_id='rocky-agent-01',
            host_id='rocky-vm-01',
            service='sshd'
        )
        enqueue_event(db_path=self.db_path, event=event3)

        result = send_buffered_events(
            db_path=self.db_path,
            host='127.0.0.1',
            port=8000,
            limit=2
        )

        self.assertEqual(result, 2)
        self.assertEqual(self.mock_send.call_args_list, [call(event=event1, host='127.0.0.1', port=8000, timeout=5.0), call(event=event2, host='127.0.0.1', port=8000, timeout=5.0)])

        check = peek_events(db_path=self.db_path, limit=10)

        self.assertEqual(check, [event3])

    # 중간 전송 실패 시 중단 검증 함수
    def test_send_stops_after_failure(self):
        event1 = SecurityEvent.create_login_failure(
            agent_id='rocky-agent-01',
            host_id='rocky-vm-01',
            service='sshd'
        )
        enqueue_event(db_path=self.db_path, event=event1)

        event2 = SecurityEvent.create_login_failure(
            agent_id='rocky-agent-01',
            host_id='rocky-vm-01',
            service='sshd'
        )
        enqueue_event(db_path=self.db_path, event=event2)

        event3 = SecurityEvent.create_login_failure(
            agent_id='rocky-agent-01',
            host_id='rocky-vm-01',
            service='sshd'
        )
        enqueue_event(db_path=self.db_path, event=event3)

        self.mock_send.side_effect = [None, OSError('전송 실패')]
        with self.assertRaises(OSError):
            send_buffered_events(
                db_path=self.db_path,
                host='127.0.0.1',
                port=8000,
                limit=3
            )

        self.assertEqual(count_events(db_path=self.db_path), 2)
        self.assertEqual(self.mock_send.call_args_list, [call(event=event1, host='127.0.0.1', port=8000, timeout=5.0), call(event=event2, host='127.0.0.1', port=8000, timeout=5.0)])

        check = peek_events(db_path=self.db_path, limit=10)

        self.assertEqual(check, [event2, event3])
