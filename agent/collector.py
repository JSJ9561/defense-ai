from agent.ssh_parser import parse_ssh_event
from common.event import SecurityEvent
from time import sleep
from os import fstat, stat
from datetime import datetime, timedelta, timezone

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
    path: str, agent_id: str, host_id: str
):
    first_open = True

    while True:
        # 파일이 없으면 잠시 대기 코드
        try:
            log_file = open(path, 'r', encoding='utf-8')
        except FileNotFoundError:
            sleep(0.2)
            continue

        with log_file:
            if first_open:
                log_file.seek(0, 2)
                first_open = False

            while True:
                position = log_file.tell()

                # 파일 잘림 감지 코드
                if fstat(log_file.fileno()).st_size < position:
                    log_file.seek(0)
                    position = log_file.tell()

                line = log_file.readline()

                # 읽을 내용이 없거나 미완성 줄이면 대기 코드
                if line == '' or not line.endswith('\n'):
                    log_file.seek(position)
                    opened_info = fstat(log_file.fileno())

                    # 경로가 없으면 잠시 대기 코드
                    try:
                        path_info = stat(path)
                    except FileNotFoundError:
                        sleep(0.2)
                        continue

                    # 파일 교체 감지 코드
                    if ((opened_info.st_dev, opened_info.st_ino) !=
                        (path_info.st_dev, path_info.st_ino)):
                        break

                    sleep(0.2)
                    continue

                # 현재 연도 확인 코드
                tzinfo = timezone(timedelta(hours=9))
                current_time = datetime.now(tzinfo)
                current_year = current_time.year

                # 지연된 연말 로그 연도 보정 코드
                parts = line.split()
                if parts:
                    if current_time.month == 1 and parts[0] == 'Dec':
                        current_year = current_year - 1

                event = parse_ssh_event(line, current_year, agent_id, host_id)

                if event is not None:
                    yield event
