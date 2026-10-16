import unittest
from unittest.mock import patch, MagicMock
from agent.runner import run_collector

# 수집 실행 테스트
class TestRunner(unittest.TestCase):
    def test_close_stream_on_write_error(self):
        stream = MagicMock()
        event = object()
        stream.__iter__.return_value = [event]

        with patch('agent.runner.follow_file', return_value=stream):
            with patch('agent.runner.append_event_jsonl', side_effect=OSError('저장실패')):
                with self.assertRaises(OSError):
                    run_collector(log_path='log_path',
                                  output_path='output_path',
                                  agent_id='rocky-agent-01',
                                  host_id='rocky-vm-01'
                                  )
                stream.close.assert_called_once_with()
