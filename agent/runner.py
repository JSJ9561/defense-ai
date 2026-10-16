from agent.collector import follow_file
from agent.output import append_event_jsonl
import argparse
import sys

# 실시간 로그 수집 및 저장 함수
def run_collector(
        log_path: str, output_path: str, agent_id: str, host_id: str
) -> None:
    stream = follow_file(path=log_path,
                         agent_id=agent_id,
                         host_id=host_id
                         )
    try:
        for event in stream:
            append_event_jsonl(path=output_path, event=event)
    finally:
        stream.close()

# 수집기 명령행 실행 함수
def main() -> int:
    parser = argparse.ArgumentParser(description='SSH 실패 로그 실시간 수집기')
    parser.add_argument('--log-path',
                        required=True,
                        help='수집할 로그 파일 경로',
                        )
    parser.add_argument('--output-path',
                        required=True,
                        help='이벤트 저장 파일 경로'
                        )
    parser.add_argument('--agent-id',
                        required=True,
                        help='에이전트 식별자'
                        )
    parser.add_argument('--host-id',
                        required=True,
                        help='호스트 식별자'
                        )

    args = parser.parse_args()

    try:
        run_collector(log_path=args.log_path,
                      output_path=args.output_path,
                      agent_id=args.agent_id,
                      host_id=args.host_id
                      )
    except KeyboardInterrupt:
        print('실시간 수집기가 종료되었습니다.')
        return 0
    except OSError as exc:
        print(f'수집 오류: {exc}', file=sys.stderr)
        return 1

    return 0

if __name__ == '__main__':
    raise SystemExit(main())
