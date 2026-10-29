import sqlite3
from common.event import SecurityEvent

# 이벤트 버퍼 초기화 함수
def initialize_buffer(
        db_path: str
) -> None:
    connection = sqlite3.connect(db_path)

    try:
        connection.execute(
            '''
            CREATE TABLE IF NOT EXISTS event_buffer
            (sequence INTEGER PRIMARY KEY,
            event_id TEXT UNIQUE NOT NULL,
            event_json TEXT NOT NULL)
            '''
        )
    finally:
        connection.close()

# 이벤트 버퍼 추가 함수
def enqueue_event(
        db_path: str, event: SecurityEvent
) -> None:
    connection = sqlite3.connect(db_path)

    try:
        connection.execute(
            '''
            INSERT INTO event_buffer
            (event_id, event_json)
            VALUES (?, ?)
            ''',
            (event.event_id, event.to_json())
        )
        connection.commit()
    finally:
        connection.close()

# 이벤트 버퍼 조회 함수
def peek_events(
        db_path: str, limit: int
) -> list[SecurityEvent]:
    if type(limit) is not int:
        raise TypeError('limit은 정수여야 합니다.')
    if limit <= 0:
        raise ValueError('limit은 양수여야 합니다.')

    connection = sqlite3.connect(db_path)

    events = []

    try:
        cursor = connection.execute(
            '''
            SELECT event_json
            FROM event_buffer
            ORDER BY sequence ASC
            LIMIT ?
            ''',
            (limit,)
        )

        rows = cursor.fetchall()

        for row in rows:
            events.append(SecurityEvent.from_json(row[0]))

        return events
    finally:
        connection.close()

# 전송 완료 이벤트 삭제 함수
def acknowledge_event(
        db_path: str, event_id: str
) -> None:
    connection = sqlite3.connect(db_path)

    try:
        connection.execute(
            '''
            DELETE FROM event_buffer
            WHERE event_id = ?
            ''',
            (event_id,)
        )
        connection.commit()
    finally:
        connection.close()

# 이벤트 버퍼 개수 조회 함수
def count_events(
        db_path: str
) -> int:
    connection = sqlite3.connect(db_path)

    try:
        cursor = connection.execute(
            '''
            SELECT COUNT(*)
            FROM event_buffer
            '''
        )

        return cursor.fetchone()[0]
    finally:
        connection.close()
