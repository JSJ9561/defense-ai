# collector 사용법

## 목적
SSH 비밀번호 로그인 실패를 SQLite 버퍼와 JSONL로 저장

## 실행 환경
Python 3.12, Rocky Linux

**저장소 최상위 디렉터리에서 root 권한으로 실행**

## 실행 명령
```
python3.12 -m agent.runner \
  --log-path /var/log/secure \
  --output-path /root/defense-events.jsonl \
  --buffer-path /root/defense-buffer.db \
  --agent-id rocky-agent-01 \
  --host-id rocky-vm-01
```

## 옵션
- --log-path: 로그 경로
- --output-path: 수집한 이벤트를 저장할 JSONL 파일 경로
- --buffer-path: 전송 대기 이벤트를 보관할 SQLite DB 파일 경로
- --agent-id: 수집 에이전트 식별자
- --host-id: 로그가 발생한 호스트 식별자

## 종료
- Ctrl + C: 종료 코드 0
- 파일 읽기, 저장 오류 및 SQLite 오류: 오류 메시지 출력 후 종료 코드 1

## 동작
- 시작 시 기존 로그는 건너뛰고 새 로그부터 수집
- 수집한 이벤트를 SQLite 버퍼에 먼저 저장한 뒤 JSONL에 저장
- 버퍼의 이벤트는 재실행 후에도 유지
- 중앙 전송은 아직 구현하지 않았으며, 현재 수집기는 버퍼 이벤트를 자동 삭제하지 않음

## 시간
원본 로그를 한국 시간으로 해석하며, 1월에 들어온 12월 로그는 전년으로 보정
