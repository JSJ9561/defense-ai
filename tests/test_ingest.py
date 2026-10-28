import sqlite3
import unittest
from pathlib import Path
from common.event import SecurityEvent, EventValidationError
from tempfile import TemporaryDirectory
from controller.storage import initialize_storage, EventConflictError
from controller.ingest import ingest_event

# 수신 이벤트 처리 테스트
class TestIngest(unittest.TestCase):
    # 정상 수신 이벤트 저장 검증 함수
    def test_ingest_valid_event(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'db'

            initialize_storage(db_path=str(path))

            event = SecurityEvent.create_login_failure(
                agent_id='rocky-agent-01',
                host_id='rocky-vm-01',
                service='sshd',
                username='user'
            )

            self.assertIs(ingest_event(db_path=str(path), event_json=event.to_json()), True)
            self.assertIs(ingest_event(db_path=str(path), event_json=event.to_json()), False)

            connection = sqlite3.connect(str(path))

            try:
                cursor = connection.execute(
                    '''
                    SELECT event_id, event_json
                    FROM security_events
                    '''
                )
                rows = cursor.fetchall()
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0][0], event.event_id)
                self.assertEqual(SecurityEvent.from_json(rows[0][1]), event)
            finally:
                connection.close()

    # 잘못된 수신 JSON 검증 함수
    def test_ingest_invalid_json(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'db'

            initialize_storage(db_path=str(path))

            with self.assertRaises(EventValidationError):
                ingest_event(db_path=str(path), event_json='invalid_jason')

            connection = sqlite3.connect(str(path))

            try:
                cursor = connection.execute(
                    '''
                    SELECT COUNT(*)
                    FROM security_events
                    '''
                )
                rows = cursor.fetchone()
                self.assertEqual(rows[0], 0)
            finally:
                connection.close()

    # 수신 이벤트 스키마 검증 함수
    def test_ingest_invalid_schema(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'db'

            initialize_storage(db_path=str(path))

            with self.assertRaises(EventValidationError):
                ingest_event(db_path=str(path), event_json='{}')

            connection = sqlite3.connect(str(path))

            try:
                cursor = connection.execute(
                    '''
                    SELECT COUNT(*)
                    FROM security_events
                    '''
                )
                rows = cursor.fetchone()
                self.assertEqual(rows[0], 0)
            finally:
                connection.close()

    # 수신 이벤트 ID 충돌 검증 함수
    def test_ingest_conflicting_event(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'db'

            initialize_storage(db_path=str(path))

            event = SecurityEvent.create_login_failure(
                agent_id='rocky-agent-01',
                host_id='rocky-vm-01',
                service='sshd',
                username='user'
            )

            ingest_event(db_path=str(path), event_json=event.to_json())

            data = event.to_dict()
            data['attributes']['username'] ='otheruser'

            conflicting_event = SecurityEvent.from_dict(data)

            with self.assertRaises(EventConflictError):
                ingest_event(db_path=str(path), event_json=conflicting_event.to_json())

            connection = sqlite3.connect(str(path))

            try:
                cursor = connection.execute(
                    '''
                    SELECT event_id, event_json
                    FROM security_events
                    '''
                )
                rows = cursor.fetchall()
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0][0], event.event_id)
                self.assertEqual(SecurityEvent.from_json(rows[0][1]), event)
            finally:
                connection.close()
