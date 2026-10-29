# Oct 13 22:29:02 defense-rocky sshd-session[3529]: Failed password for secadmin from 192.168.8.1 port 57866 ssh2
# Failed password for invalid user unknown from 192.168.8.1 port 57866 ssh2

from ipaddress import ip_address
from datetime import datetime, timedelta, timezone
from common.event import SecurityEvent

# ssh 로그인 검증 함수
def parse_ssh_login_failed(
        line: str
) -> dict[str, str] | None:
    # 대상 로그 판별 코드
    if (
        ('sshd-session[' not in line and 'sshd[' not in line)
        or 'Failed password for ' not in line
    ):
        return None

    # 실패 문구 분리 코드
    message = line.split('Failed password for ', 1)[1]
    parts = message.split()

    # 존재하지 않는 사용자 처리 코드
    if parts[:2] == ['invalid', 'user']:
        parts = parts[2:]

    # 인덱스 접근 오류 방지 및 단어 배치 검사 코드
    if len(parts) != 6:
        return None
    if parts[1] != 'from' or  parts[3] != 'port' or parts[5] != 'ssh2':
        return None

    # 포트번호 검증 코드
    if parts[4].isascii() == False or parts[4].isdecimal() == False:
        return None
    else:
        port = int(parts[4])

    if port < 1 or port > 65535:
        return None

    # username, source_ip 추출
    username = parts[0]
    source_ip = parts[2]

    # 정상 ip 검증 코드
    try:
        ip_address(source_ip)
    except ValueError:
        return None

    return {'username': username, 'source_ip': source_ip}

# 로그 시간 변환 함수
MONTHS = {
    "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
    "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
    "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
}

def parse_log_timestamp(
        line: str, year: int
) -> str | None:
    # 시간 추출 코드
    message = line.split()

    if len(message) < 3:
        return None

    # 월 매핑 코드
    month = MONTHS.get(message[0])

    if month is None:
        return None

    # 일, 시, 분, 초 자료형 변환 코드
    try:
        day = int(message[1])
    except ValueError:
        return None

    time_parts = message[2].split(':')

    if len(time_parts) != 3:
        return None

    try:
        hour = int(time_parts[0])
        minute = int(time_parts[1])
        second = int(time_parts[2])
    except ValueError:
        return None

    # 날짜 객체 생성과 범위 검증 코드
    tzinfo = timezone(timedelta(hours=9))
    try:
        local_time = datetime(
            year, month, day, hour, minute, second,
            tzinfo = tzinfo
        )
    except ValueError:
        return None

    # UTC 변환 코드
    utc_time = local_time.astimezone(timezone.utc)

    # 시간 객체 문자열로 변환 코드
    return utc_time.strftime("%Y-%m-%dT%H:%M:%SZ")

# ssh 로그를 공통 이벤트로 전환 함수
def parse_ssh_event(
    line: str, year: int, agent_id: str, host_id: str
) -> SecurityEvent | None:
    auth = parse_ssh_login_failed(line)

    # 대상이 아니거나 잘못된 인증 로그 제외 코드
    if auth is None:
        return None

    occurred_at = parse_log_timestamp(line, year)

    # 발생 시각을 해석할 수 없는 로그 제외 코드
    if occurred_at is None:
        return None

    # 공통 이벤트 생성 및 반환
    return SecurityEvent.create_login_failure(
        agent_id=agent_id,
        host_id=host_id,
        service='sshd',
        username=auth['username'],
        source_ip=auth['source_ip'],
        occurred_at=occurred_at
    )
