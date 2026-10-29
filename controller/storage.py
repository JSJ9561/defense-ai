import sqlite3
from common.event import SecurityEvent

# 이벤트 ID 충돌 예외
class EventConflictError(ValueError):
    pass

# 중앙 이벤트 저장소 초기화 함수
def initialize_storage(
        db_path: str
) -> None:
    connection = sqlite3.connect(db_path)

    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS security_events
            (event_id TEXT PRIMARY KEY NOT NULL,
            event_json TEXT NOT NULL)
            '''
        )
    finally:
        connection.close()

# 중앙 이벤트 저장 함수
def store_event(
        db_path: str, event: SecurityEvent
) -> bool:
    connection = sqlite3.connect(db_path)

    try:
        cursor = connection.execute(
            '''
            INSERT INTO security_events
            (event_id, event_json)
            VALUES (?, ?)
            ON CONFLICT(event_id) DO NOTHING
            ''',
            (event.event_id, event.to_json())
        )

        if cursor.rowcount == 1:
            connection.commit()
            return True


        cursor = connection.execute(
            '''
            SELECT event_json
            FROM security_events
            WHERE event_id = ?
            ''',
            (event.event_id,)
        )
        row = cursor.fetchone()
        stored_event = SecurityEvent.from_json(row[0])

        if stored_event == event:
            return False
        raise EventConflictError('같은 event_id에 다른 이벤트 내용이 저장되어 있습니다.')
    finally:
        connection.close()
