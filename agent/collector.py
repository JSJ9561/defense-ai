from agent.ssh_parser import parse_ssh_event
from common.event import SecurityEvent

# 로그 파일 읽고 공통 이벤트 목록 반환 함수
def collect_file(
    path: str, year: int, agent_id: str, host_id: str
) -> list[SecurityEvent]:
    events = []

    # 로그 파일 읽은 후 성공 event 추가 코드
    with open(path, "r", encoding="utf-8") as log_file:
        for line in log_file:
            event = parse_ssh_event(line, year, agent_id, host_id)

            if event is not None:
                events.append(event)

    return events
