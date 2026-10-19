# `config/` — configuración local (no versionada)

| Ruta | Rol |
|------|-----|
| `sql/.env.example` | Formato esperado de credenciales SQL locales. |
| `sql/.env.*` | Copiados por `tools/Init-SqlProfilesFromSqlFramework.ps1` (ignorados por Git). |

En la raíz del repo, `.qa-profiles.local.json` (desde `.qa-profiles.local.json.example`) enlaza perfiles SQL, `framework_root` y `boards.*` hacia **beon-pbi**.

El núcleo **no** lee `.env` automáticamente; los wrappers en `tools/` cargan el entorno antes de invocar la CLI.
