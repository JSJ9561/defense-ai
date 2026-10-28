from common.event import SecurityEvent
from controller.storage import store_event

# 수신 이벤트 검증 및 저장 함수
def ingest_event(db_path: str, event_json: str) -> bool:
    event = SecurityEvent.from_json(event_json)
    return store_event(db_path=db_path, event=event)
