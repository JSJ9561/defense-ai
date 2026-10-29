import json
from http.client import HTTPConnection
from common.event import SecurityEvent
from agent.buffer import peek_events, acknowledge_event

# 이벤트 HTTP 전송 함수
def send_event(
        host: str, port: int, event: SecurityEvent, timeout: float = 5.0
) -> None:
    body = event.to_json().encode('utf-8')
    connection = HTTPConnection(host=host, port=port, timeout=timeout)

    try:
        connection.request(
            method='POST',
            url='/events',
            body=body,
            headers={'Content-Type': 'application/json'}
        )
        response = connection.getresponse()

        if response.status != 201 and response.status != 200:
            raise RuntimeError(f'이벤트 전송 실패: HTTP {response.status}')

        response_data = json.loads(response.read().decode('utf-8'))

        if isinstance(response_data, dict) is False:
            raise RuntimeError('잘못된 서버 응답 형식')
        if response_data.get('event_id') != event.event_id:
            raise RuntimeError('서버 응답 이벤트 ID 불일치')
        if response_data.get('status') != 'stored':
            raise RuntimeError('서버 응답 저장 상태 오류')
    finally:
        connection.close()

# 버퍼 이벤트 전송 함수
def send_buffered_events(
        db_path: str, host: str, port: int, limit: int, timeout: float = 5.0
) -> int:
    events = peek_events(db_path=db_path, limit=limit)
    sent_count = 0

    for event in events:
        send_event(
            host=host,
            port=port,
            event=event,
            timeout=timeout
        )
        acknowledge_event(db_path=db_path, event_id=event.event_id)
        sent_count += 1
    return sent_count
