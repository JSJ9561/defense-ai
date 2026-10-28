import unittest
import sqlite3
from tempfile import TemporaryDirectory
from common.event import SecurityEvent
from controller.storage import initialize_storage, store_event, EventConflictError
from pathlib import Path

# 중앙 이벤트 저장소 테스트
class TestStorage(unittest.TestCase):
    # 중앙 이벤트 신규 저장 검증 함수
    def test_store_new_event(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'db'

            initialize_storage(db_path=str(path))

            event = SecurityEvent.create_login_failure(
                agent_id='rocky-agent-01',
                host_id='rocky-vm-01',
                service='sshd',
                username='user'
            )

            self.assertIs(store_event(db_path=str(path), event=event), True)

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

    # 중복 이벤트 저장 검증 함수
    def test_store_duplicate_event(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'db'

            initialize_storage(db_path=str(path))

            event = SecurityEvent.create_login_failure(
                agent_id='rocky-agent-01',
                host_id='rocky-vm-01',
                service='sshd',
                username='user'
            )

            self.assertIs(store_event(db_path=str(path), event=event), True)
            self.assertIs(store_event(db_path=str(path), event=event), False)

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

    # 중복 ID 충돌 검증 함수
    def test_store_conflicting_event(self):
        with TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / 'db'

            initialize_storage(db_path=str(path))

            event = SecurityEvent.create_login_failure(
                agent_id='rocky-agent-01',
                host_id='rocky-vm-01',
                service='sshd',
                username='user'
            )

            self.assertIs(store_event(db_path=str(path), event=event), True)

            data = event.to_dict()
            data['attributes']['username'] ='otheruser'

            conflicting_event = SecurityEvent.from_dict(data)

            with self.assertRaises(EventConflictError):
                store_event(db_path=str(path), event=conflicting_event)

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
