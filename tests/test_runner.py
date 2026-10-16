import unittest
from unittest.mock import patch, MagicMock
from agent.runner import run_collector, main

# 수집 실행 테스트
class TestRunner(unittest.TestCase):
    # 저장 오류 시 스트림 종료 검증 함수
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

    # 명령행 인자 전달 검증 함수
    def test_main_passes_arguments(self):
        argv = ['runner',
                 '--log-path', 'secure_log',
                 '--output-path', 'output_path',
                 '--agent-id', 'rocky-agent-01',
                 '--host-id', 'rocky-vm-01'
                 ]

        with patch('sys.argv', argv):
            with patch('agent.runner.run_collector') as mock_run:
                result = main()

                self.assertEqual(result, 0)

                mock_run.assert_called_once_with(log_path='secure_log',
                                                 output_path='output_path',
                                                 agent_id='rocky-agent-01',
                                                 host_id='rocky-vm-01'
                                                 )

    # 사용자 중단 시 종료 검증 함수
    def test_main_handles_keyboard_interrupt(self):
        argv = ['runner',
                 '--log-path', 'secure_log',
                 '--output-path', 'output_path',
                 '--agent-id', 'rocky-agent-01',
                 '--host-id', 'rocky-vm-01'
                 ]

        with patch('sys.argv', argv):
            with patch('agent.runner.run_collector', side_effect=KeyboardInterrupt):
                result = main()

                self.assertEqual(result, 0)

    # 파일 오류 시 실패 종료 검증 함수
    def test_main_handles_os_error(self):
        argv = ['runner',
                 '--log-path', 'secure_log',
                 '--output-path', 'output_path',
                 '--agent-id', 'rocky-agent-01',
                 '--host-id', 'rocky-vm-01'
                 ]

        with patch('sys.argv', argv):
            with patch('agent.runner.run_collector', side_effect=OSError('저장실패')):
                result = main()

                self.assertEqual(result, 1)
