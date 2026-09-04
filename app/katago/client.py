import json
import queue
import subprocess
import threading
import uuid

from app.config import KATAGO_PATH, MODEL_PATH, CONFIG_PATH


katago_process = None

# request_id -> 해당 요청이 응답을 기다리는 Queue
pending_requests = {}

# pending_requests 접근 보호
pending_lock = threading.Lock()

# stdin에 여러 요청이 동시에 쓰이는 것만 방지
write_lock = threading.Lock()


def start_katago():
    global katago_process

    katago_process = subprocess.Popen(
        [
            KATAGO_PATH,
            "analysis",
            "-model",
            MODEL_PATH,
            "-config",
            CONFIG_PATH,
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
        bufsize=1,
    )

    reader_thread = threading.Thread(
        target=read_katago_responses,
        daemon=True,
    )
    reader_thread.start()


def stop_katago():
    global katago_process

    if katago_process:
        katago_process.terminate()
        katago_process.wait()
        katago_process = None


def read_katago_responses():
    while katago_process is not None:
        response_line = katago_process.stdout.readline()

        if not response_line:
            break

        response = json.loads(response_line)
        request_id = response["id"]

        with pending_lock:
            response_queue = pending_requests.get(request_id)

        if response_queue is not None:
            response_queue.put(response)


def analyze_with_katago(query: dict) -> dict:
    if katago_process is None:
        raise RuntimeError("KataGo is not running")

    request_id = str(uuid.uuid4())

    query = {
        **query,
        "id": request_id,
    }

    response_queue = queue.Queue()

    with pending_lock:
        pending_requests[request_id] = response_queue

    try:
        request_json = json.dumps(query)

        # 요청을 stdin에 쓰는 순간만 Lock
        with write_lock:
            katago_process.stdin.write(request_json + "\n")
            katago_process.stdin.flush()

        # 자신의 UUID에 해당하는 응답을 최대 30초 기다림
        try:
            response = response_queue.get(timeout=30)
        except queue.Empty:
            raise TimeoutError(
                f"KataGo response timed out. request_id={request_id}"
            )

        return response

    finally:
        with pending_lock:
            pending_requests.pop(request_id, None)