import unittest
import sqlite3
from tempfile import TemporaryDirectory
from pathlib import Path
from common.event import SecurityEvent
from agent.buffer import peek_events
from unittest.mock import patch, MagicMock
from agent.runner import run_collector, main

# 수집 실행 테스트
class TestRunner(unittest.TestCase):
    # 저장 오류 시 스트림 종료 검증 함수
    def test_close_stream_on_write_error(self):
        stream = MagicMock()
        event = object()
        stream.__iter__.return_value = [event]

        with patch('agent.runner.initialize_buffer'):
            with patch('agent.runner.enqueue_event'):
                with patch('agent.runner.follow_file', return_value=stream):
                    with patch('agent.runner.append_event_jsonl', side_effect=OSError('저장실패')):
                        with self.assertRaises(OSError):
                            run_collector(
                                log_path='log_path',
                                output_path='output_path',
                                buffer_path='buffer_path',
                                agent_id='rocky-agent-01',
                                host_id='rocky-vm-01'
                            )
                        stream.close.assert_called_once_with()

    # 명령행 인자 전달 검증 함수
    def test_main_passes_arguments(self):
        argv = [
            'runner',
            '--log-path', 'secure_log',
            '--output-path', 'output_path',
            '--buffer-path', 'buffer_path',
            '--agent-id', 'rocky-agent-01',
            '--host-id', 'rocky-vm-01'
        ]

        with patch('sys.argv', argv):
            with patch('agent.runner.run_collector') as mock_run:
                result = main()

                self.assertEqual(result, 0)

                mock_run.assert_called_once_with(
                    log_path='secure_log',
                    output_path='output_path',
                    buffer_path='buffer_path',
                    agent_id='rocky-agent-01',
                    host_id='rocky-vm-01'
                )

    # 사용자 중단 시 종료 검증 함수
    def test_main_handles_keyboard_interrupt(self):
        argv = [
            'runner',
            '--log-path', 'secure_log',
            '--output-path', 'output_path',
            '--buffer-path', 'buffer_path',
            '--agent-id', 'rocky-agent-01',
            '--host-id', 'rocky-vm-01'
        ]

        with patch('sys.argv', argv):
            with patch('agent.runner.run_collector', side_effect=KeyboardInterrupt):
                result = main()

                self.assertEqual(result, 0)

    # 파일 오류 시 실패 종료 검증 함수
    def test_main_handles_os_error(self):
        argv = [
            'runner',
            '--log-path', 'secure_log',
            '--output-path', 'output_path',
            '--buffer-path', 'buffer_path',
            '--agent-id', 'rocky-agent-01',
            '--host-id', 'rocky-vm-01'
        ]

        with patch('sys.argv', argv):
            with patch('agent.runner.run_collector', side_effect=OSError('저장실패')):
                result = main()

                self.assertEqual(result, 1)

    # 실제 버퍼 저장 테스트
    def test_run_collector_saves_to_buffer(self):
        with TemporaryDirectory() as temp_dir:
            path_log = Path(temp_dir) / 'secure_log'
            path_json = Path(temp_dir) / 'json'
            path_db = Path(temp_dir) / 'db'
            event = SecurityEvent.create_login_failure(
                agent_id='rocky-agent-01',
                host_id='rocky-vm-01',
                service='sshd'
            )

            stream = MagicMock()
            stream.__iter__.return_value = [event]

            with patch('agent.runner.follow_file', return_value=stream):
                run_collector(
                    log_path=str(path_log),
                    output_path=str(path_json),
                    buffer_path=str(path_db),
                    agent_id='rocky-agent-01',
                    host_id='rocky-vm-01'
                )

            peek = peek_events(db_path=str(path_db), limit=10)
            json_text = path_json.read_text(encoding='utf-8')


            self.assertEqual(peek, [event])
            self.assertEqual(SecurityEvent.from_json(json_text), event)

            stream.close.assert_called_once_with()

    # SQLite 오류 처리 검증 함수
    def test_main_handles_sqlite_error(self):
        argv = [
            'runner',
            '--log-path', 'secure_log',
            '--output-path', 'output_path',
            '--buffer-path', 'buffer_path',
            '--agent-id', 'rocky-agent-01',
            '--host-id', 'rocky-vm-01'
        ]

        with patch('sys.argv', argv):
            with patch('agent.runner.run_collector', side_effect=sqlite3.OperationalError('버퍼 저장실패')):
                result = main()

                self.assertEqual(result, 1)
