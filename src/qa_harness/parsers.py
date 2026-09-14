from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from .common import ContractError, MAX_REPORT_BYTES, read_json, aggregate
from .contract import validate_named


def parse_results(path, format_name, run_id, control_id, phase):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > MAX_REPORT_BYTES:
        raise ContractError("Reporte ausente o demasiado grande")
    metadata = {}
    if format_name == "json":
        payload = read_json(path)
        validate_named(payload, "results")
        if (payload["run_id"], payload["control_id"], payload["phase"]) != (run_id, control_id, phase):
            raise ContractError("Reporte pertenece a otra ejecucion/control/fase")
        tests = payload["tests"]
        metadata = payload.get("metadata", {})
    else:
        raw = path.read_bytes()
        try:
            text = raw.decode("utf-8-sig")
            if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
                raise ContractError("DTD/entidades XML no permitidas")
            tree = ET.fromstring(text)
        except (UnicodeError, ET.ParseError) as exc:
            raise ContractError("JUnit XML invalido") from exc
        if tree.tag not in ("testsuite", "testsuites"):
            raise ContractError("Raiz JUnit desconocida")
        tests = []
        for case in tree.iter("testcase"):
            name = case.get("name", "").strip()
            if not name:
                raise ContractError("JUnit sin nombre de test")
            identifier = f"{case.get('classname', '')}::{name}"
            statuses = ["error" if e.tag == "error" else "failed" if e.tag == "failure" else "skipped"
                        for e in case if e.tag in ("error", "failure", "skipped")]
            status = aggregate(statuses) if statuses else "passed"
            if statuses == ["skipped"]:
                status = "skipped"
            tests.append({"id": identifier, "status": status,
                          "message": "\n".join((e.get("message", "") + " " + (e.text or "")).strip()
                                               for e in case if e.tag in ("error", "failure", "skipped"))})
        for suite in tree.iter():
            if suite.tag in ("testsuite", "testsuites") and "tests" in suite.attrib:
                try:
                    declared = int(suite.attrib["tests"])
                except ValueError as exc:
                    raise ContractError("Conteo JUnit invalido") from exc
                if declared != len(list(suite.iter("testcase"))):
                    raise ContractError("Conteo JUnit no coincide con casos presentes")
    ids = [test["id"] for test in tests]
    if len(ids) != len(set(ids)):
        raise ContractError("Resultados con IDs duplicados")
    return tests, metadata
