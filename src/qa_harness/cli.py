from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from . import __version__
from .common import CODES, ContractError
from .gate import evaluate
from .reporting import load_report, markdown
from .board_profiles import resolve_board_from_ref
from .pbi_filter_scope import run_filter_scope
from .pbi_kpi_month import run_month_oracles
from .pbi_por_hoja import run_filtros_por_hoja, run_kpi_por_hoja, run_visuales_por_hoja
from .corrida_planilla import run_corrida_planilla
from .planilla_qa import export_planilla, load_corrida_json, load_planilla_catalog
from .runner import check, run
from .sql_profiles import harness_root, load_local_profiles_config


def main(argv=None):
    parser = argparse.ArgumentParser(prog="qa-harness", description="QA reproducible sobre un checkout explicito")
    parser.add_argument("--version", action="version", version=__version__)
    subs = parser.add_subparsers(dest="command", required=True)
    for name in ("check", "run"):
        sub = subs.add_parser(name)
        sub.add_argument("--repo", required=True, type=Path)
        sub.add_argument("--manifest", default="qa.json")
        sub.add_argument("--profile", required=True)
        if name == "run":
            sub.add_argument("--control", action="append")
            sub.add_argument("--output", help="Directorio nuevo dentro de .qa-runs/")
            sub.add_argument("--retry", type=int, default=0, choices=(0, 1, 2))
            sub.add_argument("--allow-isolated-write", action="store_true",
                             help="Confirma una ejecucion SQL con escritura aislada declarada.")
    sub = subs.add_parser("report")
    sub.add_argument("--input", required=True, type=Path)
    sub = subs.add_parser("gate")
    sub.add_argument("--repo", required=True, type=Path)
    sub.add_argument("--input", required=True, type=Path)
    sub.add_argument("--decisions", type=Path)
    sub = subs.add_parser(
        "pbi-kpi-month",
        help="Oráculos KPI mensuales Softys (from-dax vs from-definition) vía beon-pbi + perfil SQL local",
    )
    sub.add_argument(
        "--profile",
        required=True,
        help="Perfil en .qa-profiles.local.json (ej. staging)",
    )
    sub.add_argument("--harness-root", type=Path, help="Raíz qa-ia-harness (default: autodetect)")
    sub.add_argument("--board", help="ID en boards.* de .qa-profiles.local.json (default: default_board)")
    sub.add_argument(
        "--ref",
        help="Ruta arrastrada al .Report, .pbip o .SemanticModel (alternativa a --board)",
    )
    sub.add_argument("--kpi", help="Solo un kpi_id (opcional)")
    sub.add_argument("--timeout", type=int, default=600, help="Timeout segundos ODBC/SQL")
    sub = subs.add_parser(
        "pbi-filter-scope",
        help="Filtros del reporte vs scope-filters.json (valores vía SQL DimStore/DimCategory/DimKeyword)",
    )
    sub.add_argument("--profile", required=True, help="Perfil en .qa-profiles.local.json (ej. staging)")
    sub.add_argument("--harness-root", type=Path, help="Raíz qa-ia-harness (default: autodetect)")
    sub.add_argument("--board", help="ID en boards.* (default: default_board)")
    sub.add_argument("--ref", help="Ruta al .Report / .pbip (alternativa a --board)")
    sub.add_argument("--timeout", type=int, default=180, help="Timeout segundos ODBC/SQL")
    sub = subs.add_parser(
        "pbi-kpi-por-hoja",
        help="Indicadores por hoja del informe (oráculo SQL + catálogo); --hoja opcional",
    )
    sub.add_argument("--profile", required=True)
    sub.add_argument("--harness-root", type=Path)
    sub.add_argument("--board")
    sub.add_argument("--ref")
    sub.add_argument(
        "--hoja",
        help="Nombre visible o identificador interno de una hoja; si se omite, todas",
    )
    sub.add_argument("--timeout", type=int, default=600)
    sub = subs.add_parser(
        "pbi-filtros-por-hoja",
        help="Filtros contractuales por hoja (scope-filters.json + SQL)",
    )
    sub.add_argument("--profile", required=True)
    sub.add_argument("--harness-root", type=Path)
    sub.add_argument("--board")
    sub.add_argument("--ref")
    sub.add_argument("--hoja")
    sub.add_argument("--timeout", type=int, default=180)
    sub = subs.add_parser(
        "pbi-visuales-por-hoja",
        help="Cada visual por hoja vs contrato, filtros SQL y oráculo de indicadores",
    )
    sub.add_argument("--profile", required=True)
    sub.add_argument("--harness-root", type=Path)
    sub.add_argument("--board")
    sub.add_argument("--ref")
    sub.add_argument("--hoja")
    sub.add_argument("--timeout", type=int, default=600)
    sub = subs.add_parser(
        "export-planilla",
        help="Armar salida tipo Google Sheet (recorrida o regresión) desde JSON de corridas",
    )
    sub.add_argument(
        "--catalog",
        required=True,
        type=Path,
        help="manual-cases/planilla-catalog.json del consumidor",
    )
    sub.add_argument("--kpi", type=Path, help="Salida JSON de pbi-kpi-por-hoja")
    sub.add_argument("--filtros", type=Path, help="Salida JSON de pbi-filtros-por-hoja")
    sub.add_argument("--visuales", type=Path, help="Salida JSON de pbi-visuales-por-hoja")
    sub.add_argument(
        "--modo",
        required=True,
        choices=("recorrida", "regresion"),
        help="recorrida: pisa bloque de revisión en la pestaña existente; regresion: nueva pestaña",
    )
    sub.add_argument(
        "--revision",
        type=int,
        default=1,
        help="Índice de bloque Revision N a actualizar en recorrida (default 1)",
    )
    sub.add_argument(
        "--hoja-planilla",
        help="Título de pestaña existente (recorrida), ej. 'Revision 14/10/26'",
    )
    sub.add_argument(
        "--nombre-hoja-nueva",
        help="Título de pestaña nueva (regresión); default Revision DD/MM/AAAA",
    )
    sub.add_argument(
        "--entrada-previa",
        type=Path,
        help="export-planilla.json anterior para conservar revisiones o filtrar fallidos",
    )
    sub.add_argument(
        "--solo-fallidos-anterior",
        action="store_true",
        help="En regresión, solo filas que quedaron en Error en la corrida previa",
    )
    sub.add_argument(
        "--output",
        type=Path,
        help="Escribir JSON completo (incluye sheets_patch y grid_csv)",
    )
    sub.add_argument(
        "--csv",
        type=Path,
        help="Escribir grid CSV importable a Google Sheets",
    )
    sub = subs.add_parser(
        "corrida-planilla",
        help="KPI + filtros + visuales + export-planilla en test-evidence del consumidor",
    )
    sub.add_argument("--profile", required=True)
    sub.add_argument("--harness-root", type=Path)
    sub.add_argument("--board")
    sub.add_argument("--ref")
    sub.add_argument("--modo", required=True, choices=("recorrida", "regresion"))
    sub.add_argument("--revision", type=int, default=1)
    sub.add_argument("--hoja-planilla")
    sub.add_argument("--nombre-hoja-nueva")
    sub.add_argument("--entrada-previa", type=Path)
    sub.add_argument("--solo-fallidos-anterior", action="store_true")
    sub.add_argument("--evidence-dir", type=Path)
    sub.add_argument("--timeout", type=int, default=600)
    sub = subs.add_parser(
        "planilla-cobertura",
        help="Reporte enlace catálogo planilla ↔ JSON de corrida (sin publicar Sheets)",
    )
    sub.add_argument("--catalog", required=True, type=Path)
    sub.add_argument("--kpi", type=Path)
    sub.add_argument("--filtros", type=Path)
    sub.add_argument("--visuales", type=Path)
    sub.add_argument("--bindings", type=Path, help="planilla-harness-bindings.json")
    sub.add_argument("--output", type=Path)
    sub = subs.add_parser(
        "resolve-board",
        help="Resolver board_id, version_id y rutas PBIP desde una referencia arrastrada",
    )
    sub.add_argument("--harness-root", type=Path, help="Raíz qa-ia-harness (default: autodetect)")
    sub.add_argument(
        "--ref",
        default="",
        help="Ruta o @repo/.../Tablero.Report (vacío = default_board)",
    )
    args = parser.parse_args(argv)
    try:
        if args.command == "check":
            result = check(args.repo.resolve(), args.manifest, args.profile)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return CODES[result["status"]]
        if args.command == "run":
            result, destination = run(args.repo, args.manifest, args.profile, args.control, args.output, args.retry,
                                      args.allow_isolated_write)
            print(json.dumps({"status": result["status"], "exit_code": result["exit_code"],
                              "exploratory": result["exploratory"], "report": str(destination / "report.json")},
                             ensure_ascii=False, indent=2))
            return result["exit_code"]
        if args.command == "report":
            print(markdown(load_report(args.input)))
            return 0
        if args.command == "pbi-kpi-month":
            if args.board and args.ref:
                raise ContractError("Usar solo --board o --ref en pbi-kpi-month.")
            result = run_month_oracles(
                harness_root_path=args.harness_root.resolve() if args.harness_root else None,
                profile=args.profile,
                board_id=args.board,
                board_ref=args.ref,
                kpi_id=args.kpi,
                timeout_seconds=args.timeout,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return int(result["exit_code"])
        if args.command == "pbi-filter-scope":
            if args.board and args.ref:
                raise ContractError("Usar solo --board o --ref en pbi-filter-scope.")
            result = run_filter_scope(
                harness_root_path=args.harness_root.resolve() if args.harness_root else None,
                profile=args.profile,
                board_id=args.board,
                board_ref=args.ref,
                timeout_seconds=args.timeout,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return int(result["exit_code"])
        if args.command in (
            "pbi-kpi-por-hoja",
            "pbi-filtros-por-hoja",
            "pbi-visuales-por-hoja",
        ):
            if args.board and args.ref:
                raise ContractError(f"Usar solo --board o --ref en {args.command}.")
            timeout = getattr(args, "timeout", 600)
            common = {
                "harness_root_path": args.harness_root.resolve() if args.harness_root else None,
                "profile": args.profile,
                "board_id": args.board,
                "board_ref": args.ref,
                "hoja": getattr(args, "hoja", None),
                "timeout_seconds": timeout,
            }
            if args.command == "pbi-kpi-por-hoja":
                result = run_kpi_por_hoja(**common)
            elif args.command == "pbi-filtros-por-hoja":
                result = run_filtros_por_hoja(**common)
            else:
                result = run_visuales_por_hoja(**common)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return int(result["codigo_salida"])
        if args.command == "export-planilla":
            catalog = load_planilla_catalog(args.catalog.resolve())
            from .planilla_qa import load_tablero_aliases

            catalog_dir = args.catalog.resolve().parent
            aliases_path = catalog_dir.parent / "planilla-tablero-aliases.json"
            if not aliases_path.is_file():
                aliases_path = catalog_dir / "planilla-tablero-aliases.json"
            tablero_aliases = load_tablero_aliases(aliases_path)
            from .planilla_bindings import load_planilla_bindings
            from .planilla_qa import default_planilla_bindings_path

            bindings_path = (
                args.bindings.resolve()
                if getattr(args, "bindings", None)
                else default_planilla_bindings_path(catalog_dir.parent)
            )
            planilla_bindings = load_planilla_bindings(bindings_path)
            prev = (
                load_corrida_json(args.entrada_previa.resolve())
                if args.entrada_previa
                else None
            )
            kpi = load_corrida_json(args.kpi.resolve()) if args.kpi else None
            filtros = load_corrida_json(args.filtros.resolve()) if args.filtros else None
            visuales = load_corrida_json(args.visuales.resolve()) if args.visuales else None
            if args.modo == "recorrida" and not args.hoja_planilla:
                src_title = (catalog.get("source") or {}).get("sheet_title")
                if not src_title:
                    raise ContractError(
                        "recorrida requiere --hoja-planilla o sheet_title en el catálogo."
                    )
                hoja_planilla = src_title
            else:
                hoja_planilla = args.hoja_planilla
            result = export_planilla(
                catalog=catalog,
                kpi=kpi,
                filtros=filtros,
                visuales=visuales,
                tablero_aliases=tablero_aliases or None,
                planilla_bindings=planilla_bindings,
                modo=args.modo,
                revision_index=args.revision,
                nombre_hoja_nueva=args.nombre_hoja_nueva,
                hoja_planilla=hoja_planilla,
                entrada_previa=prev,
                solo_fallidos_anterior=args.solo_fallidos_anterior,
            )
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(
                    json.dumps(result, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            if args.csv:
                args.csv.parent.mkdir(parents=True, exist_ok=True)
                args.csv.write_text(result["grid_csv"], encoding="utf-8-sig")
            if args.output:
                print(
                    json.dumps(
                        {
                            "escrito": str(args.output.resolve()),
                            "resumen": result.get("resumen"),
                            "publish_plan_pasos": len(
                                (result.get("publish_plan") or {}).get("pasos") or []
                            ),
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                )
            else:
                print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        if args.command == "planilla-cobertura":
            from .planilla_bindings import build_linkage_report, load_planilla_bindings
            from .planilla_qa import (
                build_automation_index,
                default_planilla_bindings_path,
                load_tablero_aliases,
            )

            catalog = load_planilla_catalog(args.catalog.resolve())
            catalog_dir = args.catalog.resolve().parent
            aliases_path = catalog_dir.parent / "planilla-tablero-aliases.json"
            tablero_aliases = load_tablero_aliases(aliases_path)
            bindings_path = (
                args.bindings.resolve()
                if args.bindings
                else default_planilla_bindings_path(catalog_dir.parent)
            )
            planilla_bindings = load_planilla_bindings(bindings_path)
            kpi = load_corrida_json(args.kpi.resolve()) if args.kpi else None
            filtros = load_corrida_json(args.filtros.resolve()) if args.filtros else None
            visuales = load_corrida_json(args.visuales.resolve()) if args.visuales else None
            index = build_automation_index(kpi, filtros, visuales)
            report = build_linkage_report(
                catalog,
                kpi=kpi,
                filtros=filtros,
                visuales=visuales,
                bindings_doc=planilla_bindings,
                tablero_aliases=tablero_aliases or None,
                automation_index=index,
            )
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(
                    json.dumps(report, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            print(json.dumps({"resumen": report["resumen"]}, ensure_ascii=False, indent=2))
            return 0
        if args.command == "corrida-planilla":
            if args.board and args.ref:
                raise ContractError("Usar solo --board o --ref en corrida-planilla.")
            result = run_corrida_planilla(
                harness_root_path=args.harness_root.resolve() if args.harness_root else None,
                profile=args.profile,
                board_id=args.board,
                board_ref=args.ref,
                modo=args.modo,
                revision_index=args.revision,
                hoja_planilla=args.hoja_planilla,
                nombre_hoja_nueva=args.nombre_hoja_nueva,
                entrada_previa_path=args.entrada_previa,
                solo_fallidos_anterior=args.solo_fallidos_anterior,
                evidence_dir=args.evidence_dir.resolve() if args.evidence_dir else None,
                timeout_seconds=args.timeout,
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return int(result["codigo_salida"])
        if args.command == "resolve-board":
            root = args.harness_root.resolve() if args.harness_root else harness_root()
            config = load_local_profiles_config(root)
            ref = (args.ref or "").strip() or None
            board_id, entry, ctx = resolve_board_from_ref(root, config, ref)
            label = entry.get("label") if isinstance(entry.get("label"), str) else None
            payload = {
                "board_id": board_id,
                "label": label or ctx.get("board_yml_label"),
                "version_id": ctx.get("version_id"),
                "resolution": ctx,
            }
            print(json.dumps(payload, ensure_ascii=False, indent=2))
            return 0
        result = evaluate(args.repo, args.input, args.decisions)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return result["exit_code"]
    except subprocess.TimeoutExpired:
        print(json.dumps({"status": "error", "exit_code": 2, "message": "Timeout SQL"}, ensure_ascii=False), file=sys.stderr)
        return 2
    except (ContractError, OSError) as exc:
        print(json.dumps({"status": "error", "exit_code": 2, "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print('{"status":"cancelled","exit_code":3}', file=sys.stderr)
        return 3
