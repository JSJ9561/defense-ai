import sqlite3
import json
import argparse
import sys
from common.event import SecurityEvent
from common.event import EventValidationError
from controller.storage import EventConflictError, initialize_storage
from http.server import BaseHTTPRequestHandler, HTTPServer
from controller.ingest import ingest_event

# 이벤트 HTTP 요청 처리 클래스
class EventRequestHandler(BaseHTTPRequestHandler):
    db_path: str

    # 이벤트 POST 요청 처리 함수
    def do_POST(self):
        if self.path != '/events':
            self.send_error(404, 'Not Found')
            return

        content_length = self.headers.get('Content-Length')

        if content_length is None:
            self.send_error(411, 'Length Required')
            return

        try:
            length = int(content_length)
        except ValueError:
            self.send_error(400, 'Invalid Content-Length')
            return

        if length <= 0:
            self.send_error(400, 'Invalid Content-Length')
            return
        if length > 65536:
            self.send_error(413, 'Payload Too Large')
            return

        body = self.rfile.read(length)
        if len(body) != length:
            self.send_error(400, 'Incomplete Request Body')
            return

        try:
            event_json = body.decode('utf-8')
        except UnicodeDecodeError:
            self.send_error(400, 'Invalid UTF-8')
            return

        try:
            created = ingest_event(db_path=self.db_path, event_json=event_json)
        except EventValidationError:
            self.send_error(400, 'Invalid Event')
            return
        except EventConflictError:
            self.send_error(409, 'Event ID Conflict')
            return
        except sqlite3.Error:
            self.send_error(500, 'Storage Error')
            return

        if created is True:
            status_code = 201
        else:
            status_code = 200

        event = SecurityEvent.from_json(event_json)

        response = {'event_id': event.event_id, 'status': 'stored'}

        response_body = json.dumps(response).encode('utf-8')
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(response_body)))
        self.end_headers()
        self.wfile.write(response_body)

# 중앙 이벤트 수신 서버 실행 함수
def run_server(host: str, port: int, db_path: str) -> None:
    initialize_storage(db_path=db_path)
    EventRequestHandler.db_path = db_path
    server = HTTPServer((host, port), EventRequestHandler)

    try:
        server.serve_forever()
    finally:
        server.server_close()

# 중앙 수신 서버 명령행 실행 함수
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--host',
        default='127.0.0.1'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=8000
    )
    parser.add_argument(
        '--db-path',
        required=True
    )
    args = parser.parse_args()

    try:
        run_server(
            host=args.host,
            port=args.port,
            db_path=args.db_path
        )
    except KeyboardInterrupt:
        print('종료')
        return 0
    except (OSError, sqlite3.Error) as exc:
        print(f'오류: {exc}', file=sys.stderr)
        return 1

    return 0

if __name__ == '__main__':
    raise SystemExit(main())
