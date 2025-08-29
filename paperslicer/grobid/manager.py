import os, shutil, subprocess, time
from typing import Optional
import requests

DEFAULT_IMAGE = "lfoppiano/grobid:0.8.1"
DEFAULT_URL = "http://localhost:8070"

class GrobidManager:
    """
    Manages a local GROBID service.
    - is_available(): check HTTP health
    - start(): try to start Docker container (detached)
    """
    def __init__(self, base_url: Optional[str] = None, image: str = DEFAULT_IMAGE):
        self.base_url = (base_url or os.getenv("GROBID_URL") or DEFAULT_URL).rstrip("/")
        self.image = image

    def is_available(self, timeout_s: float = 1.0) -> bool:
        try:
            r = requests.get(self.base_url, timeout=timeout_s)
            return r.status_code < 500
        except Exception:
            return False

    def start(self, port: int = 8070, wait_ready_s: int = 20) -> bool:
        """Attempt to start GROBID via Docker; returns True if becomes ready."""
        if self.is_available():
            return True
        if shutil.which("docker") is None:
            return False  # no docker, can’t autostart
        # start detached
        try:
            subprocess.Popen(
                ["docker", "run", "-t", "--rm", "-p", f"{port}:8070", self.image],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception:
            return False
        # wait until healthy
        for _ in range(wait_ready_s):
            if self.is_available(timeout_s=0.5):
                return True
            time.sleep(1)
        return False