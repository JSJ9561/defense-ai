from common.event import SecurityEvent

# 공통 이벤트 JSONL 저장 함수
def append_event_jsonl(
        path: str, event: SecurityEvent
) -> None:
    with open(path, 'a', encoding='utf-8') as output_file:
        output_file.write(event.to_json() + '\n')
