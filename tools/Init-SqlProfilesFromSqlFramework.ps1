# Sincroniza perfiles de conexion desde qa-sql-testing-framework hacia qa-ia-harness.
# No commitea secretos: solo copia a config/sql/ (gitignored) y genera .qa-profiles.local.json.
param(
    [string]$SqlFrameworkRoot = "",
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$harnessRoot = Split-Path -Parent $PSScriptRoot

if (-not $SqlFrameworkRoot) {
    $examplePath = Join-Path $harnessRoot '.qa-profiles.local.json.example'
    if (Test-Path -LiteralPath $examplePath) {
        $example = Get-Content -LiteralPath $examplePath -Raw | ConvertFrom-Json
        $SqlFrameworkRoot = $example.sql_framework_root
    }
    if (-not $SqlFrameworkRoot) {
        $SqlFrameworkRoot = '../qa-sql-testing-framework'
    }
}

$sqlRoot = [System.IO.Path]::GetFullPath((Join-Path $harnessRoot $SqlFrameworkRoot))
if (-not (Test-Path -LiteralPath $sqlRoot)) {
    throw "No se encontro qa-sql-testing-framework en: $sqlRoot"
}

$destDir = Join-Path $harnessRoot 'config/sql'
New-Item -ItemType Directory -Force -Path $destDir | Out-Null

$map = @{
    'local'   = '.env.local'
    'test'    = '.env.test'
    'prod'    = '.env.prod'
    'staging' = '.env.test'
}

foreach ($pair in $map.GetEnumerator()) {
    $src = Join-Path $sqlRoot $pair.Value
    $destName = if ($pair.Key -eq 'staging') { '.env.test' } else { ".env.$($pair.Key)" }
    if ($pair.Key -eq 'prod') { $destName = '.env.prod' }
    $dest = Join-Path $destDir $destName
    if (-not (Test-Path -LiteralPath $src)) {
        Write-Warning "Omite $($pair.Key): no existe $src"
        continue
    }
    if ((Test-Path -LiteralPath $dest) -and -not $Force) {
        Write-Host "Mantiene existente: $dest (use -Force para sobrescribir)"
        continue
    }
    Copy-Item -LiteralPath $src -Destination $dest -Force
    Write-Host "Copiado: $($pair.Value) -> $dest"
}

# .env activo del framework (opcional) como config/sql/.env para herramientas que lo esperan
$activeSrc = Join-Path $sqlRoot '.env'
$activeDest = Join-Path $destDir '.env'
if (Test-Path -LiteralPath $activeSrc) {
    if (-not (Test-Path -LiteralPath $activeDest) -or $Force) {
        Copy-Item -LiteralPath $activeSrc -Destination $activeDest -Force
        Write-Host "Copiado: .env activo -> $activeDest"
    }
}

$profilesPath = Join-Path $harnessRoot '.qa-profiles.local.json'
$exampleProfiles = Join-Path $harnessRoot '.qa-profiles.local.json.example'
if (-not (Test-Path -LiteralPath $profilesPath) -or $Force) {
    Copy-Item -LiteralPath $exampleProfiles -Destination $profilesPath -Force
    $cfg = Get-Content -LiteralPath $profilesPath -Raw | ConvertFrom-Json
    $cfg.sql_framework_root = $SqlFrameworkRoot
    $cfg | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $profilesPath -Encoding utf8
    Write-Host "Generado: $profilesPath"
} else {
    Write-Host "Mantiene: $profilesPath (use -Force para regenerar desde example)"
}

Write-Host ""
Write-Host "Uso:"
Write-Host "  .\tools\Invoke-QAProfile.ps1 -Profile local qa-harness run --repo <consumidor> --profile <perfil-qa-json>"
Write-Host "  .\tools\Invoke-QAProfile.ps1 -Profile staging ..."
