from agent.ssh_parser import parse_ssh_event
from common.event import SecurityEvent
from time import sleep

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

# 새 로그를 계속 읽어 이벤트를 전달하는 함수
def follow_file(
    path: str, year: int, agent_id: str, host_id: str
):
    with open(path, "r", encoding="utf-8") as log_file:
        log_file.seek(0, 2)

        while True:
            position = log_file.tell()
            line = log_file.readline()

            # 빈 문자열이면 잠시 대기하는 코드
            if line == '':
                sleep(0.2)
                continue

            # 아직 기록이 끝나지 않은 줄 대기 코드
            if not line.endswith('\n'):
                log_file.seek(position)
                sleep(0.2)
                continue

            event = parse_ssh_event(line, year, agent_id, host_id)

            if event is not None:
                yield event
