# Arquitectura — qa-ia-harness

Este documento describe cómo encajan la CLI, los repos consumidores (por ejemplo **beon-pbi**) y el rol opcional de Cursor.

## Vista general

```mermaid
flowchart TB
  subgraph humano["Humano / QA"]
    QRD["QRD + qa.json\n(repo consumidor)"]
    CUR["Cursor Agent\n(comandos /Calculo*)"]
  end

  subgraph harness["qa-ia-harness"]
    CLI["qa-harness CLI"]
    CORE["Núcleo genérico\ncheck · run · gate"]
    PBI["Extensiones PBI\nKPI · filtros · visuales · planilla"]
    PROV["Provenance\ncommit, hashes, .qa-runs/"]
  end

  subgraph consumidor["Repo consumidor (ej. beon-pbi)"]
    PBIP[".pbip / .Report / .SemanticModel"]
    QA_GLOBAL["qa/kpi-definitions"]
    QA_BOARD["&lt;Cliente&gt;/qa\nSQL, catálogo, evidencia"]
  end

  subgraph datos["Datos"]
    SQL["SQL Server\n(perfil local/test)"]
    SHEETS["Google Sheets\n(planilla opcional)"]
  end

  QRD --> CORE
  CUR --> CLI
  CLI --> CORE
  CLI --> PBI
  CORE --> PROV
  PBI --> QA_GLOBAL
  PBI --> QA_BOARD
  PBI --> PBIP
  PBI --> SQL
  PBI --> SHEETS
  QA_BOARD --> SQL
```

## Flujo típico — tablero Power BI (Softys u otro)

```mermaid
sequenceDiagram
  participant U as Usuario / Agent
  participant H as qa-harness
  participant B as beon-pbi
  participant DB as SQL Server
  participant SHEETS as Google Sheets

  U->>H: resolve-board --ref Softys.pbip
  H->>B: Lee board.yml, client.yml, rutas PBIP
  U->>H: pbi-kpi-month / corrida-planilla
  H->>B: Ejecuta scripts en Cliente/qa/sql/
  B->>DB: Consultas read-only (oráculos)
  DB-->>B: Resultados
  B-->>H: JSON compare / por-hoja
  H->>B: test-evidence/*.json
  opt Planilla
    H->>H: export-planilla / publish_plan
    U->>SHEETS: MCP Google Sheets
  end
  U->>H: gate (si hay qa.json en consumidor)
```

## Principios

| Idea | Detalle |
|------|---------|
| Sin reglas de negocio en el núcleo | KPI, scope y catálogo viven en **beon-pbi** (`qa/`, `<Cliente>/qa/`). |
| Sin IA en la ejecución | Los comandos son deterministas; Cursor solo orquesta y documenta. |
| Evidencia fuera de Git | Salidas en `.qa-runs/` o `test-evidence/` según el flujo. |
| Perfiles locales | `.qa-profiles.local.json` enlaza harness ↔ framework SQL ↔ cada tablero. |

## Módulos Python (mapa rápido)

Ver `src/qa_harness/README.md` para el detalle por archivo.

## Documentación relacionada

- [Contrato y CLI](contract.md)
- [Integración Cursor](../integrations/cursor/README.md)
- Repo consumidor **beon-pbi**: `qa/README.md` y `Softys/qa/README.md` (mismo workspace multi-root).
