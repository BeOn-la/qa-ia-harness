"""Genera planilla-harness-bindings.json desde el catálogo (reglas por plantilla de caso)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qa_harness.planilla_bindings import default_filter_phrases, default_kpi_phrases
from qa_harness.planilla_qa import load_planilla_catalog

KPI_EXTRA = {
    "in stock": "stock-compliance",
    "qimages": "qimages-compliance",
    "q images": "qimages-compliance",
}


def main() -> int:
    if len(sys.argv) < 3:
        print(
            "Uso: gen_planilla_harness_bindings.py <planilla-catalog.json> <salida.json>",
            file=sys.stderr,
        )
        return 2
    catalog = load_planilla_catalog(Path(sys.argv[1]).resolve())
    out_path = Path(sys.argv[2]).resolve()

    reglas: list[dict] = []
    rid = 0

    def add(
        *,
        caso_contains: str | list[str],
        binding: dict | None,
        cobertura: str,
        nota: str,
        tipo_prueba: str | None = None,
    ) -> None:
        nonlocal rid
        rid += 1
        m: dict = {"caso_contains": caso_contains}
        if tipo_prueba:
            m["tipo_prueba"] = tipo_prueba
        reglas.append(
            {
                "id": f"r{rid:03d}",
                "match": m,
                "binding": binding,
                "cobertura_harness": cobertura,
                "nota": nota,
            }
        )

    kpi_phrases = {**default_kpi_phrases(), **KPI_EXTRA}
    for phrase, kpi_id in sorted(kpi_phrases.items(), key=lambda x: -len(x[0])):
        add(
            caso_contains=f"validar kpi {phrase}",
            binding={"capa": "indicadores", "kpi_id": kpi_id},
            cobertura="harness",
            nota=f"Oráculo mensual KPI {kpi_id} (puede ser no aplica si no se muestra en la hoja).",
        )
        add(
            caso_contains=phrase,
            binding={"capa": "indicadores", "kpi_id": kpi_id},
            cobertura="harness",
            nota=f"KPI {kpi_id} mencionado en caso compuesto (gráficos/tablas).",
            tipo_prueba="KPI/Calculos",
        )

    for phrase, fid in default_filter_phrases():
        add(
            caso_contains=f"validar filtro de {phrase}",
            binding={"capa": "filtros", "filter_id": fid},
            cobertura="harness",
            nota=f"Contrato scope-filters + SQL ({fid}).",
            tipo_prueba="Filtros",
        )
        add(
            caso_contains=phrase,
            binding={"capa": "filtros", "filter_id": fid},
            cobertura="harness",
            nota=f"Filtro {fid} en título abreviado.",
            tipo_prueba="Filtros",
        )

    add(
        caso_contains="alcance contractual de indicadores",
        binding={"capa": "alcance"},
        cobertura="harness",
        nota="scope-kpis vs visibles en PBIP.",
    )
    add(
        caso_contains="estetica general de la pagina",
        binding={"capa": "visuales_resumen"},
        cobertura="harness",
        nota="Resumen de visuales (solo estética general).",
    )
    add(
        caso_contains="colorcoding",
        binding={"capa": "visuales_resumen"},
        cobertura="harness",
        nota="Resumen de visuales (colorcoding).",
    )

    manual_phrases = [
        ("terciary image", "KPI no definido en catálogo técnico QA."),
        ("quaternary image", "KPI no definido en catálogo técnico QA."),
        ("rating", "KPI Rating: fuera de oráculos SQL actuales."),
        ("# reviews", "KPI Reviews: fuera de oráculos SQL actuales."),
    ]
    for phrase, nota in manual_phrases:
        add(
            caso_contains=phrase,
            binding=None,
            cobertura="manual",
            nota=nota,
        )

    doc = {
        "schema_version": 1,
        "descripcion": (
            "Enlace entre filas de la planilla Google y resultados de corrida "
            "(KPI/filtros/visuales). No modifica qué prueba el harness."
        ),
        "kpi_phrases": kpi_phrases,
        "filter_phrases": [{"phrase": p, "filter_id": f} for p, f in default_filter_phrases()],
        "reglas": reglas,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"escrito": str(out_path), "reglas": len(reglas)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
