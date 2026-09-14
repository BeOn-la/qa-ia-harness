"""SQL Server preflight with an explicit, optional pyodbc dependency.

This module never loads dotenv files and never writes a connection string to a
report. It is intended to be called as a manifest preflight command.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def enabled(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    return default if value is None else value.strip().lower() in {"1", "true", "yes", "on"}


def connection_string() -> str:
    server_name = os.environ[os.environ["QA_SQL_SERVER_ENV"]]
    database_name = os.environ[os.environ["QA_SQL_DATABASE_ENV"]]
    profile_kind = os.getenv("QA_PROFILE_KIND", "")
    encrypt = os.getenv("MSSQL_ENCRYPT", "yes").strip().lower()
    trust_certificate = enabled("MSSQL_TRUST_SERVER_CERTIFICATE", False)
    if encrypt not in {"yes", "true", "1", "mandatory", "optional", "no", "false", "0"}:
        raise RuntimeError("MSSQL_ENCRYPT invalido")
    if encrypt in {"optional", "no", "false", "0"} and profile_kind != "local":
        raise RuntimeError("TLS obligatorio fuera del perfil local")
    if trust_certificate and profile_kind != "local":
        raise RuntimeError("TrustServerCertificate solo se permite en perfil local")

    parts = [
        f"DRIVER={{{os.getenv('MSSQL_ODBC_DRIVER', 'ODBC Driver 18 for SQL Server')}}}",
        f"SERVER={server_name}",
        f"DATABASE={database_name}",
        "Encrypt=yes" if encrypt in {"yes", "true", "1", "mandatory"} else "Encrypt=optional",
        f"TrustServerCertificate={'yes' if trust_certificate else 'no'}",
    ]
    if enabled("MSSQL_TRUSTED_CONNECTION", False):
        parts.append("Trusted_Connection=yes")
    else:
        user = os.getenv("MSSQL_USER", "")
        password = os.getenv("MSSQL_PASSWORD", "")
        if not user or not password:
            raise RuntimeError("Falta autenticacion SQL Server")
        parts.extend((f"UID={user}", f"PWD={password}"))
        authentication = os.getenv("MSSQL_AUTHENTICATION", "SqlPassword").strip()
        if authentication.upper() != "NONE":
            parts.append(f"Authentication={authentication}")
    return ";".join(parts) + ";"


def inspect_target(connect):
    query = """
    SELECT
      COALESCE(CONVERT(nvarchar(256), SERVERPROPERTY('ServerName')), @@SERVERNAME),
      DB_NAME(),
      CONVERT(nvarchar(256), SERVERPROPERTY('ProductVersion')),
      SUSER_SNAME(), ORIGINAL_LOGIN(), USER_NAME(),
      HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'INSERT'),
      HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'UPDATE'),
      HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'DELETE'),
      HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'ALTER ANY SCHEMA'),
      HAS_PERMS_BY_NAME(DB_NAME(), 'DATABASE', 'CREATE TABLE');
    """
    with connect(connection_string(), timeout=int(os.getenv("MSSQL_LOGIN_TIMEOUT", "15"))) as connection:
        cursor = connection.cursor()
        cursor.timeout = int(os.getenv("MSSQL_QUERY_TIMEOUT", "120"))
        cursor.execute(query)
        row = cursor.fetchone()
    names = ("insert", "update", "delete", "alter_any_schema", "create_table")
    permissions = {name: bool(row[index + 6]) for index, name in enumerate(names)}
    return {
        "server": str(row[0]), "database": str(row[1]), "engine_version": str(row[2]),
        "principal": str(row[3]), "original_login": str(row[4]), "database_user": str(row[5]),
        "database_write_permissions": permissions,
        "baseline_sha256": os.environ.get("QA_SQL_BASELINE_SHA256", ""),
    }


def payload(status: str, target: dict | None = None, message: str = "") -> dict:
    access = os.getenv("QA_SQL_ACCESS", "")
    test = {"id": "sqlserver-identity", "status": status}
    metadata = {"target": target or {}, "sql_access": access}
    if access == "isolated_write":
        metadata["write_scope"] = {"kind": os.getenv("QA_SQL_WRITE_SCOPE_KIND", ""),
                                   "value": os.getenv("QA_SQL_WRITE_SCOPE_VALUE", "")}
    return {"schema_version": 1, "run_id": os.environ["QA_RUN_ID"],
            "control_id": os.environ["QA_CONTROL_ID"], "phase": os.environ["QA_PHASE"],
            "tests": [test], "metadata": metadata, "message": message}


def main() -> int:
    report_path = Path(os.environ["QA_REPORT_PATH"])
    try:
        try:
            import pyodbc
        except ImportError as exc:
            raise RuntimeError("Falta dependencia opcional pyodbc para preflight SQL Server") from exc
        target = inspect_target(pyodbc.connect)
        if os.getenv("QA_SQL_ACCESS") == "read_only" and any(target["database_write_permissions"].values()):
            result = payload("failed", target, "La identidad read_only conserva permisos de escritura a nivel base")
            code = 1
        else:
            result = payload("passed", target)
            code = 0
    except Exception as exc:
        result = payload("error", message=f"Preflight SQL Server no completado: {type(exc).__name__}")
        code = 2
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(result, ensure_ascii=False), encoding="utf-8")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
