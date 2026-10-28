import unittest
import json
import sqlite3
from unittest.mock import patch
from controller.server import main
from pathlib import Path
from tempfile import TemporaryDirectory
from http.server import HTTPServer
from controller.server import EventRequestHandler
from controller.storage import initialize_storage
from threading import Thread
from common.event import SecurityEvent
from http.client import HTTPConnection

# 서버 테스트
class TestServer(unittest.TestCase):
    # 서버 명령행 인자 전달 검증 함수
    def test_main_passes_arguments(self):
        argv = [
            'main',
            '--host', '127.0.0.1',
            '--port', '8000',
            '--db-path', 'test.db'
        ]

        with patch('sys.argv', argv):
            with patch('controller.server.run_server') as mock_run:
                result = main()

                self.assertEqual(result, 0)

                mock_run.assert_called_once_with(
                    host='127.0.0.1',
                    port=8000,
                    db_path='test.db'
                )

    # HTTP 이벤트 저장 검증 함수
    def test_post_stores_event(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'db_path'

            with patch.object(
                EventRequestHandler,
                'db_path',
                str(path),
                create=True
            ):
                initialize_storage(db_path=str(path))
                server = HTTPServer(('127.0.0.1', 0), EventRequestHandler)

                thread = Thread(target=server.serve_forever, daemon=True)
                thread.start()

                port = server.server_address[1]
                connection = HTTPConnection('127.0.0.1', port, timeout=5)

                try:
                    event = SecurityEvent.create_login_failure(
                        agent_id='rocky-agent-01',
                        host_id='rocky-vm-01',
                        service='sshd'
                    )
                    body = event.to_json().encode('utf-8')

                    connection.request(
                        method='POST',
                        url='/events',
                        body=body,
                        headers={'Content-Type': 'application/json'}
                    )
                    response = connection.getresponse()

                    self.assertEqual(response.status, 201)
                    response_data = json.loads(response.read().decode('utf-8'))
                    self.assertEqual(response_data['event_id'], event.event_id)
                    self.assertEqual(response_data['status'], 'stored')

                    connection.request(
                        method='POST',
                        url='/events',
                        body=body,
                        headers={'Content-Type': 'application/json'}
                    )
                    response = connection.getresponse()

                    self.assertEqual(response.status, 200)
                    response_data = json.loads(response.read().decode('utf-8'))
                    self.assertEqual(response_data['event_id'], event.event_id)
                finally:
                    connection.close()
                    server.shutdown()
                    thread.join()
                    server.server_close()

    # 잘못된 json 검증 함수
    def test_post_rejects_invalid_json(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'db_path'

            with patch.object(
                EventRequestHandler,
                'db_path',
                str(path),
                create=True
            ):
                initialize_storage(db_path=str(path))
                server = HTTPServer(('127.0.0.1', 0), EventRequestHandler)

                thread = Thread(target=server.serve_forever, daemon=True)
                thread.start()

                port = server.server_address[1]
                connection = HTTPConnection('127.0.0.1', port, timeout=5)

                try:
                    body = b'{'
                    connection.request(
                        method='POST',
                        url='/events',
                        body=body,
                        headers={'Content-Type': 'application/json'}
                    )
                    response = connection.getresponse()

                    self.assertEqual(response.status, 400)
                    response.read()
                finally:
                    connection.close()
                    server.shutdown()
                    thread.join()
                    server.server_close()

    # 이벤트 스키마 검증 함수
    def test_post_rejects_invalid_schema(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'db_path'

            with patch.object(
                EventRequestHandler,
                'db_path',
                str(path),
                create=True
            ):
                initialize_storage(db_path=str(path))
                server = HTTPServer(('127.0.0.1', 0), EventRequestHandler)

                thread = Thread(target=server.serve_forever, daemon=True)
                thread.start()

                port = server.server_address[1]
                connection = HTTPConnection('127.0.0.1', port, timeout=5)

                try:
                    body = b'{}'
                    connection.request(
                        method='POST',
                        url='/events',
                        body=body,
                        headers={'Content-Type': 'application/json'}
                    )
                    response = connection.getresponse()

                    self.assertEqual(response.status, 400)
                    response.read()
                finally:
                    connection.close()
                    server.shutdown()
                    thread.join()
                    server.server_close()

    # 이벤트 ID 충돌 검증 함수
    def test_post_rejects_conflicting_event(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'db_path'

            with patch.object(
                EventRequestHandler,
                'db_path',
                str(path),
                create=True
            ):
                initialize_storage(db_path=str(path))
                server = HTTPServer(('127.0.0.1', 0), EventRequestHandler)

                thread = Thread(target=server.serve_forever, daemon=True)
                thread.start()

                port = server.server_address[1]
                connection = HTTPConnection('127.0.0.1', port, timeout=5)

                try:
                    event = SecurityEvent.create_login_failure(
                        agent_id='rocky-agent-01',
                        host_id='rocky-vm-01',
                        service='sshd'
                    )
                    body = event.to_json().encode('utf-8')

                    connection.request(
                        method='POST',
                        url='/events',
                        body=body,
                        headers={'Content-Type': 'application/json'}
                    )
                    response = connection.getresponse()

                    self.assertEqual(response.status, 201)
                    response_data = json.loads(response.read().decode('utf-8'))
                    self.assertEqual(response_data['event_id'], event.event_id)
                    self.assertEqual(response_data['status'], 'stored')

                    conflicting_data = json.loads(event.to_json())
                    conflicting_data['attributes']['service'] = 'other-service'
                    body = json.dumps(conflicting_data).encode('utf-8')

                    connection.request(
                        method='POST',
                        url='/events',
                        body=body,
                        headers={'Content-Type': 'application/json'}
                    )
                    response = connection.getresponse()

                    self.assertEqual(response.status, 409)
                    response.read()
                finally:
                    connection.close()
                    server.shutdown()
                    thread.join()
                    server.server_close()

    # 저장소 오류 응답 검증 함수
    def test_post_return_storage_error(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'db_path'

            with patch.object(
                EventRequestHandler,
                'db_path',
                str(path),
                create=True
            ):
                initialize_storage(db_path=str(path))
                server = HTTPServer(('127.0.0.1', 0), EventRequestHandler)

                thread = Thread(target=server.serve_forever, daemon=True)
                thread.start()

                port = server.server_address[1]
                connection = HTTPConnection('127.0.0.1', port, timeout=5)

                try:
                    event = SecurityEvent.create_login_failure(
                        agent_id='rocky-agent-01',
                        host_id='rocky-vm-01',
                        service='sshd'
                    )
                    body = event.to_json().encode('utf-8')

                    with patch(
                        'controller.server.ingest_event',
                        side_effect=sqlite3.Error('test storage error')
                    ):
                        connection.request(
                            method='POST',
                            url='/events',
                            body=body,
                            headers={'Content-Type': 'application/json'}
                        )
                        response = connection.getresponse()

                        self.assertEqual(response.status, 500)
                        response.read()
                finally:
                    connection.close()
                    server.shutdown()
                    thread.join()
                    server.server_close()

    # 잘못된 요청 경로 검증 함수
    def test_post_rejects_unknown_path(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'db_path'

            with patch.object(
                EventRequestHandler,
                'db_path',
                str(path),
                create=True
            ):
                initialize_storage(db_path=str(path))
                server = HTTPServer(('127.0.0.1', 0), EventRequestHandler)

                thread = Thread(target=server.serve_forever, daemon=True)
                thread.start()

                port = server.server_address[1]
                connection = HTTPConnection('127.0.0.1', port, timeout=5)

                try:
                    event = SecurityEvent.create_login_failure(
                        agent_id='rocky-agent-01',
                        host_id='rocky-vm-01',
                        service='sshd'
                    )
                    body = event.to_json().encode('utf-8')

                    connection.request(
                        method='POST',
                        url='/unknown',
                        body=body,
                        headers={'Content-Type': 'application/json'}
                    )
                    response = connection.getresponse()

                    self.assertEqual(response.status, 404)
                    response.read()
                finally:
                    connection.close()
                    server.shutdown()
                    thread.join()
                    server.server_close()

    # 요청 본문 크기 제한 검증 함수
    def test_post_rejects_large_body(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'db_path'

            with patch.object(
                EventRequestHandler,
                'db_path',
                str(path),
                create=True
            ):
                initialize_storage(db_path=str(path))
                server = HTTPServer(('127.0.0.1', 0), EventRequestHandler)

                thread = Thread(target=server.serve_forever, daemon=True)
                thread.start()

                port = server.server_address[1]
                connection = HTTPConnection('127.0.0.1', port, timeout=5)

                try:
                    event = SecurityEvent.create_login_failure(
                        agent_id='rocky-agent-01',
                        host_id='rocky-vm-01',
                        service='sshd'
                    )
                    body = b''

                    connection.request(
                        method='POST',
                        url='/events',
                        body=body,
                        headers={'Content-Length': '65537'}
                    )
                    response = connection.getresponse()

                    self.assertEqual(response.status, 413)
                    response.read()
                finally:
                    connection.close()
                    server.shutdown()
                    thread.join()
                    server.server_close()

    # 잘못된 UTF-8 검증 함수
    def test_post_rejects_invalid_utf8(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'db_path'

            with patch.object(
                EventRequestHandler,
                'db_path',
                str(path),
                create=True
            ):
                initialize_storage(db_path=str(path))
                server = HTTPServer(('127.0.0.1', 0), EventRequestHandler)

                thread = Thread(target=server.serve_forever, daemon=True)
                thread.start()

                port = server.server_address[1]
                connection = HTTPConnection('127.0.0.1', port, timeout=5)

                try:
                    event = SecurityEvent.create_login_failure(
                        agent_id='rocky-agent-01',
                        host_id='rocky-vm-01',
                        service='sshd'
                    )
                    body = b'\xff'

                    connection.request(
                        method='POST',
                        url='/events',
                        body=body,
                        headers={'Content-Type': 'application/json'}
                    )
                    response = connection.getresponse()

                    self.assertEqual(response.status, 400)
                    response.read()
                finally:
                    connection.close()
                    server.shutdown()
                    thread.join()
                    server.server_close()

    # 잘못된 본문 길이 헤더 검증 함수
    def test_post_rejects_invalid_content_length(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'db_path'

            with patch.object(
                EventRequestHandler,
                'db_path',
                str(path),
                create=True
            ):
                initialize_storage(db_path=str(path))
                server = HTTPServer(('127.0.0.1', 0), EventRequestHandler)

                thread = Thread(target=server.serve_forever, daemon=True)
                thread.start()

                port = server.server_address[1]
                connection = HTTPConnection('127.0.0.1', port, timeout=5)

                try:
                    event = SecurityEvent.create_login_failure(
                        agent_id='rocky-agent-01',
                        host_id='rocky-vm-01',
                        service='sshd'
                    )
                    body = b'{}'

                    connection.request(
                        method='POST',
                        url='/events',
                        body=body,
                        headers={'Content-Length': 'abc'}
                    )
                    response = connection.getresponse()

                    self.assertEqual(response.status, 400)
                    response.read()
                finally:
                    connection.close()
                    server.shutdown()
                    thread.join()
                    server.server_close()

    # 빈 요청 본문 검증 함수
    def test_post_rejects_empty_body(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'db_path'

            with patch.object(
                EventRequestHandler,
                'db_path',
                str(path),
                create=True
            ):
                initialize_storage(db_path=str(path))
                server = HTTPServer(('127.0.0.1', 0), EventRequestHandler)

                thread = Thread(target=server.serve_forever, daemon=True)
                thread.start()

                port = server.server_address[1]
                connection = HTTPConnection('127.0.0.1', port, timeout=5)

                try:
                    event = SecurityEvent.create_login_failure(
                        agent_id='rocky-agent-01',
                        host_id='rocky-vm-01',
                        service='sshd'
                    )
                    body = b''

                    connection.request(
                        method='POST',
                        url='/events',
                        body=body,
                        headers={'Content-Length': '0'}
                    )
                    response = connection.getresponse()

                    self.assertEqual(response.status, 400)
                    response.read()
                finally:
                    connection.close()
                    server.shutdown()
                    thread.join()
                    server.server_close()

    # 본문 길이 헤더 누락 검증 함수
    def test_post_rejects_missing_content_length(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'db_path'

            with patch.object(
                EventRequestHandler,
                'db_path',
                str(path),
                create=True
            ):
                initialize_storage(db_path=str(path))
                server = HTTPServer(('127.0.0.1', 0), EventRequestHandler)

                thread = Thread(target=server.serve_forever, daemon=True)
                thread.start()

                port = server.server_address[1]
                connection = HTTPConnection('127.0.0.1', port, timeout=5)

                try:
                    event = SecurityEvent.create_login_failure(
                        agent_id='rocky-agent-01',
                        host_id='rocky-vm-01',
                        service='sshd'
                    )

                    connection.putrequest(
                        method='POST',
                        url='/events',
                    )
                    connection.endheaders()
                    response = connection.getresponse()

                    self.assertEqual(response.status, 411)
                    response.read()
                finally:
                    connection.close()
                    server.shutdown()
                    thread.join()
                    server.server_close()
