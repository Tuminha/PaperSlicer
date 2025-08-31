import os, shutil, subprocess, time
from typing import Optional
import requests

DEFAULT_IMAGE = "lfoppiano/grobid:0.8.1"
DEFAULT_URL = "http://localhost:8070"
DEFAULT_CONTAINER = os.getenv("GROBID_CONTAINER_NAME", "paperslicer-grobid")

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

    def start(self, port: int = 8070, wait_ready_s: int = 20, detach: bool = True) -> bool:
        """Attempt to start GROBID via Docker; returns True if becomes ready.

        Uses a named container (paperslicer-grobid by default) and detaches by default.
        """
        if self.is_available():
            return True
        # 1) Try Docker if available
        if shutil.which("docker") is not None:
            try:
                args = [
                    "docker", "run",
                    "--rm",
                    "-p", f"{port}:8070",
                    "--name", DEFAULT_CONTAINER,
                ]
                if detach:
                    args.insert(2, "-d")
                # pull image if missing; ignore errors
                try:
                    subprocess.run(["docker", "pull", self.image], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                except Exception:
                    pass
                args.append(self.image)
                subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                # wait until healthy
                for _ in range(wait_ready_s):
                    if self.is_available(timeout_s=0.5):
                        return True
                    time.sleep(1)
            except Exception:
                # fall through to local start
                pass
        # 2) Try local command via env GROBID_RUN_CMD
        run_cmd = os.getenv("GROBID_RUN_CMD")
        if run_cmd:
            try:
                subprocess.Popen(run_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                for _ in range(wait_ready_s):
                    if self.is_available(timeout_s=0.5):
                        return True
                    time.sleep(1)
            except Exception:
                pass
        # 3) Try GROBID_HOME with Gradle runner
        grobid_home = os.getenv("GROBID_HOME")
        if grobid_home:
            svc = os.path.join(grobid_home, "grobid-service")
            gradlew = os.path.join(svc, "gradlew")
            if os.path.isfile(gradlew):
                try:
                    subprocess.Popen(["./gradlew", "run"], cwd=svc, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    for _ in range(wait_ready_s):
                        if self.is_available(timeout_s=0.5):
                            return True
                        time.sleep(1)
                except Exception:
                    pass
        return False

    def ensure_running(self) -> bool:
        """Ensure a GROBID service is reachable; try to start if not available."""
        if self.is_available():
            return True
        return self.start()
