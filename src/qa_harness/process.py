from __future__ import annotations

import base64
import hashlib
import os
import re
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.parse import quote

from .common import ContractError, artifact, aggregate, contained
from .parsers import parse_results

MAX_OUTPUT = 2 * 1024 * 1024
BASE_ENV = ("PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "COMSPEC", "TEMP", "TMP",
            "LANG", "LC_ALL", "LD_LIBRARY_PATH")


def environment(profile):
    env = {key: os.environ[key] for key in BASE_ENV if key in os.environ}
    for key in profile["pass_env"]:
        if key in os.environ:
            env[key] = os.environ[key]
    env.update(PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1", PYTHONDONTWRITEBYTECODE="1", CI="true")
    return env, [os.environ[name] for name in profile["secret_env"] if os.environ.get(name)]


def redact(text, secrets):
    for secret in sorted(secrets, key=len, reverse=True):
        for value in {secret, repr(secret)[1:-1], quote(secret, safe=""),
                      base64.b64encode(secret.encode()).decode()}:
            if value:
                text = text.replace(value, "[REDACTED]")
    return re.sub(r"(?i)(password|pwd|token|secret)(\s*[=:]\s*)[^\s;]+", r"\1\2[REDACTED]", text)


def terminate_tree(process):
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
    else:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=10)


def execute(root, command, destination, run_id, control_id, phase, profile):
    destination.mkdir(parents=True, exist_ok=False)
    env, secrets = environment(profile)
    started = time.monotonic()
    result = {"phase": phase, "status": "error", "exit_code": None, "tests": [],
              "metadata": {}, "artifacts": [], "message": "", "duration_seconds": 0.0}
    with tempfile.TemporaryDirectory(prefix="qa-process-") as raw_dir:
        raw_dir = Path(raw_dir)
        report = raw_dir / ("results.json" if command["format"] == "json" else "results.xml")
        substitutions = {"{python}": sys.executable, "{report}": str(report),
                         "{root}": str(root), "{run_id}": run_id}
        argv = []
        for part in command["argv"]:
            for key, value in substitutions.items():
                part = part.replace(key, value)
            if any(secret in part for secret in secrets):
                raise ContractError("No pasar secretos como argumentos")
            argv.append(part)
        env.update(QA_REPORT_PATH=str(report), QA_RUN_ID=run_id, QA_CONTROL_ID=control_id,
                   QA_PHASE=phase, QA_PROFILE=profile["name"], QA_PROFILE_KIND=profile["kind"], QA_ROOT=str(root))
        if profile.get("sql_target"):
            target = profile["sql_target"]
            env["QA_EXPECTED_SQL_SERVER"] = target["expected_server"]
            env["QA_EXPECTED_SQL_DATABASE"] = target["expected_database"]
            env["QA_EXPECTED_SQL_PRINCIPALS"] = ",".join(target["expected_principals"])
            env["QA_SQL_SERVER_ENV"] = target["server_env"]
            env["QA_SQL_DATABASE_ENV"] = target["database_env"]
            env["QA_SQL_ACCESS"] = profile["sql_access"]
            env["QA_SQL_BASELINE_SHA256"] = hashlib.sha256(
                contained(root, target["baseline"], exists=True).read_bytes()).hexdigest()
            if profile["sql_access"] == "isolated_write":
                env["QA_SQL_WRITE_SCOPE_KIND"] = profile["write_scope"]["kind"]
                env["QA_SQL_WRITE_SCOPE_VALUE"] = profile["write_scope"]["value"]
        process = None
        interrupted = False
        safe_report = report
        try:
            with (raw_dir / "stdout").open("wb") as out, (raw_dir / "stderr").open("wb") as err:
                process = subprocess.Popen(argv, cwd=contained(root, command["cwd"], exists=True),
                                           env=env, stdin=subprocess.DEVNULL, stdout=out, stderr=err,
                                           shell=False, start_new_session=os.name != "nt")
                while process.poll() is None:
                    if time.monotonic() - started > command["timeout_seconds"]:
                        result["message"] = "Timeout; arbol de procesos terminado"
                        terminate_tree(process)
                        break
                    if any(p.stat().st_size > MAX_OUTPUT for p in (raw_dir / "stdout", raw_dir / "stderr")):
                        result["message"] = "Limite de salida excedido"
                        terminate_tree(process)
                        break
                    time.sleep(0.025)
                result["exit_code"] = process.returncode
        except KeyboardInterrupt:
            interrupted = True
            result["status"] = "cancelled"
            result["message"] = "Ejecucion cancelada"
        except (OSError, subprocess.SubprocessError) as exc:
            result["message"] = f"No se pudo ejecutar: {type(exc).__name__}"
        finally:
            if process is not None:
                terminate_tree(process)
        for name in ("stdout", "stderr"):
            raw_path = raw_dir / name
            text = raw_path.read_bytes()[:MAX_OUTPUT].decode("utf-8", errors="replace") if raw_path.exists() else ""
            saved = destination / (name + ".log")
            saved.write_text(redact(text, secrets), encoding="utf-8")
            result["artifacts"].append(artifact(saved, destination.parents[2]))
        if report.is_file():
            if report.stat().st_size <= 10 * 1024 * 1024:
                safe_report = destination / report.name
                try:
                    safe_report.write_text(redact(report.read_text(encoding="utf-8-sig"), secrets), encoding="utf-8")
                    result["artifacts"].append(artifact(safe_report, destination.parents[2]))
                except UnicodeError:
                    result["message"] = "Reporte con codificacion invalida"
            else:
                result["message"] = "Reporte demasiado grande"
        if not result["message"]:
            try:
                tests, metadata = parse_results(safe_report, command["format"], run_id, control_id, phase)
                result["tests"], result["metadata"] = tests, metadata
                result["status"] = aggregate(test["status"] for test in tests)
                if result["exit_code"] != 0 and result["status"] != "failed":
                    result["status"] = "error"
                    result["message"] = "Salida del proceso incompatible con resultado aprobado/incompleto"
                if phase != "execute" and result["status"] != "passed":
                    result["status"] = "error"
            except (ContractError, OSError) as exc:
                result["status"] = "error"
                result["message"] = str(exc)
        if interrupted:
            result["status"] = "cancelled"
        result["duration_seconds"] = round(time.monotonic() - started, 3)
    return result
