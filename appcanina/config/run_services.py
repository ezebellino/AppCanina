"""Supervise web and push worker together on the existing Railway volume."""
import os
import signal
import subprocess
import sys
import time


def main():
    children = []
    stopping = False

    def stop(*_):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        children.append(subprocess.Popen(["gunicorn", "config.wsgi:application", "--bind",
            "0.0.0.0:" + os.environ.get("PORT", "8000"), "--workers", "1", "--access-logfile", "-", "--error-logfile", "-"]))
        if os.environ.get("PUSH_WORKER_ENABLED", "1") == "1":
            children.append(subprocess.Popen([sys.executable, "manage.py", "process_push"]))
        while not stopping and all(child.poll() is None for child in children):
            time.sleep(1)
        return 0 if stopping else 1  # Railway restarts the unit if either process fails.
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()


if __name__ == "__main__":
    sys.exit(main())
