"""Consumer-owned SQL checks against an explicitly labelled disposable container.

Uses sqlcmd already installed in the Microsoft SQL Server image: no host ODBC or
database credentials are needed outside this disposable fixture.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
SERVER = "qa-harness-sql"
DATABASE = "qa_harness_demo"


def container():
    name = os.environ.get("QA_SQL_CONTAINER", "")
    if not name or not re.fullmatch(r"[A-Za-z0-9_.-]+", name):
        raise RuntimeError("Falta contenedor SQL de fixture")
    process = subprocess.run(["docker", "inspect", name], capture_output=True, text=True, timeout=15)
    if process.returncode:
        raise RuntimeError("Contenedor no disponible")
    data = json.loads(process.stdout)[0]
    config = data["Config"]
    if config.get("Labels", {}).get("qa-harness-fixture") != "true" or config["Hostname"] != SERVER:
        raise RuntimeError("Contenedor no autorizado como fixture")
    if os.environ.get("QA_SQL_DATABASE") != DATABASE or os.environ.get("QA_SQL_SERVER") != "localhost":
        raise RuntimeError("Destino no autorizado")
    return name


def sql(query, database=DATABASE):
    name = container()
    env = os.environ.copy()
    env["SQLCMDPASSWORD"] = os.environ["QA_SQL_PASSWORD"]
    # With Docker's `none` network, localhost can resolve to IPv6 while SQL Server
    # only accepts the IPv4 loopback connection inside this disposable fixture.
    args = ["docker", "exec", "--env", "SQLCMDPASSWORD", name, "/opt/mssql-tools18/bin/sqlcmd",
            "-S", "127.0.0.1,1433", "-U", "sa", "-C", "-b", "-r", "1", "-h", "-1", "-W",
            "-s", "|", "-d", database, "-Q", "SET NOCOUNT ON; " + query]
    result = subprocess.run(args, capture_output=True, text=True, env=env, timeout=30)
    if result.returncode:
        # Do not persist driver diagnostics that might expose connection information.
        raise RuntimeError("sqlcmd fallo; no hay evidencia de validacion aprobada")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def identity(database=DATABASE):
    rows = sql("SELECT CONVERT(varchar(128),SERVERPROPERTY('ServerName')), DB_NAME(), "
               "CONVERT(varchar(128),SERVERPROPERTY('ProductVersion')), SUSER_SNAME();", database)
    if len(rows) != 1:
        raise RuntimeError("Respuesta de identidad SQL invalida")
    server, actual_db, version, principal = rows[0].split("|")
    if server != SERVER or actual_db != database:
        raise RuntimeError("Identidad SQL efectiva no permitida")
    return {"server": server, "database": actual_db, "engine_version": version, "principal": principal,
            "baseline_sha256": hashlib.sha256((HERE / "baseline.sql").read_bytes()).hexdigest()}


def main():
    phase = sys.argv[1]
    if phase == "bootstrap":
        identity("master")
        sql(f"IF DB_ID(N'{DATABASE}') IS NULL CREATE DATABASE [{DATABASE}];", "master")
        identity()
        print("Base sintetica preparada")
        return 0
    tests, metadata = [], {}
    try:
        metadata["target"] = identity()
        run_id = os.environ["QA_RUN_ID"]
        if not re.fullmatch(r"[a-f0-9]{32}-a[1-3]", run_id):
            raise RuntimeError("ID de ejecucion invalido")
        table = "qa_" + run_id.replace("-", "_")
        if phase == "preflight":
            tests = [{"id": "target", "status": "passed"}]
        elif phase == "setup":
            sql((HERE / "baseline.sql").read_text(encoding="utf-8").format(table=table))
            count = sql(f"SELECT COUNT(*) FROM dbo.[{table}];")
            tests = [{"id": "seed", "status": "passed" if count == ["5"] else "failed"}]
        elif phase == "execute":
            condition = "Url IS NULL" if os.environ.get("QA_DEMO_BUG") == "1" else "Url IS NULL OR LTRIM(RTRIM(Url)) = '-'"
            actual = [int(row) for row in sql(f"SELECT Id FROM dbo.[{table}] WHERE {condition} ORDER BY Id;")]
            for test_id, ok in [("seed_present", sql(f"SELECT COUNT(*) FROM dbo.[{table}];") == ["5"]),
                                ("null_and_hyphens", actual == [1, 2, 3]),
                                ("valid_and_empty_excluded", 4 not in actual and 5 not in actual)]:
                tests.append({"id": test_id, "status": "passed" if ok else "failed"})
        elif phase == "cleanup":
            sql(f"DROP TABLE IF EXISTS dbo.[{table}];")
            absent = sql(f"SELECT CASE WHEN OBJECT_ID(N'dbo.{table}', N'U') IS NULL THEN 1 ELSE 0 END;")
            tests = [{"id": "cleanup_verified", "status": "passed" if absent == ["1"] else "failed"}]
        else:
            raise RuntimeError("Fase no reconocida")
    except Exception as exc:
        tests = [{"id": "infrastructure", "status": "error", "message": str(exc)}]
    result = {"schema_version": 1, "run_id": os.environ["QA_RUN_ID"],
              "control_id": os.environ["QA_CONTROL_ID"], "phase": phase,
              "tests": tests, "metadata": metadata}
    Path(os.environ["QA_REPORT_PATH"]).write_text(json.dumps(result), encoding="utf-8")
    return 2 if any(t["status"] == "error" for t in tests) else 1 if any(t["status"] == "failed" for t in tests) else 0

if __name__ == "__main__":
    raise SystemExit(main())
