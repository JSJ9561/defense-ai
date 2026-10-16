from agent.collector import follow_file
from agent.output import append_event_jsonl

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
