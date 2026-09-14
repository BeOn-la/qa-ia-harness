"""Create, test and remove only an owned SQL Server fixture container."""
import importlib.util
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
import uuid

HERE = Path(__file__).resolve().parent
IMAGE = "mcr.microsoft.com/mssql/server@sha256:7c29dfbac885ad7519e219c7fe4aee0e67283e21a10e9c252d13b0fbde1866f8"


def main():
    name = "qa-harness-fixture-" + uuid.uuid4().hex[:12]
    env = os.environ.copy()
    password = secrets.token_urlsafe(28) + "aA1!"
    env.update(MSSQL_SA_PASSWORD=password, QA_SQL_PASSWORD=password,
               QA_SQL_SERVER="localhost", QA_SQL_DATABASE="qa_harness_demo",
               QA_SQL_CONTAINER=name, ACCEPT_EULA="Y")
    owned = False
    try:
        process = subprocess.run(["docker", "run", "--detach", "--name", name,
                                  "--hostname", "qa-harness-sql", "--label", "qa-harness-fixture=true",
                                  "--network", "none", "--env", "ACCEPT_EULA",
                                  "--env", "MSSQL_SA_PASSWORD", "--env", "MSSQL_PID=Developer", IMAGE],
                                 env=env, capture_output=True, text=True, timeout=180)
        if process.returncode:
            raise RuntimeError("No se pudo iniciar el contenedor SQL; revisar Docker y disponibilidad de imagen")
        owned = True
        deadline = time.monotonic() + 120
        ready = False
        while time.monotonic() < deadline:
            probe = subprocess.run([sys.executable, str(HERE / "checks.py"), "bootstrap"],
                                   env=env, capture_output=True, timeout=40)
            if probe.returncode == 0:
                ready = True
                break
            time.sleep(2)
        if not ready:
            raise RuntimeError("SQL Server no estuvo listo dentro del plazo; no se ejecutaron validaciones")
        process = subprocess.run([sys.executable, str(HERE.parent / "verify.py"), "sql"], env=env, timeout=180)
        return process.returncode
    finally:
        if owned:
            # Exact generated name, owned label and hostname; never enumerate/delete other containers.
            inspected = subprocess.run(["docker", "inspect", name], capture_output=True, text=True, timeout=15)
            if inspected.returncode == 0:
                data = json.loads(inspected.stdout)[0]
                if data["Config"].get("Labels", {}).get("qa-harness-fixture") != "true":
                    raise RuntimeError("El contenedor cambio de identidad; no se elimina")
                removed = subprocess.run(["docker", "rm", "--force", name], capture_output=True, timeout=30)
                if removed.returncode:
                    raise RuntimeError(f"No se pudo retirar el contenedor de fixture {name}")


if __name__ == "__main__":
    raise SystemExit(main())
