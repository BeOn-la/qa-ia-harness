[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('local', 'staging', 'production')]
    [string]$Profile,

    [Parameter(Mandatory, ValueFromRemainingArguments)]
    [string[]]$Command
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$configPath = Join-Path $root '.qa-profiles.local.json'
if (-not (Test-Path -LiteralPath $configPath)) {
    throw 'Falta .qa-profiles.local.json. Crear una configuracion local ignorada por Git.'
}

$config = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
$profileConfig = $config.profiles.$Profile
if ($null -eq $profileConfig -or $profileConfig.execution -ne 'allowed') {
    throw "El perfil '$Profile' no esta habilitado para ejecucion."
}
if ($Profile -eq 'production') {
    throw 'Produccion no es un perfil ejecutable del harness.'
}

$envPath = Join-Path $root $profileConfig.env_file
if (-not (Test-Path -LiteralPath $envPath)) {
    throw "No existe el archivo de perfil local: $($profileConfig.env_file)"
}

$original = @{}
$changed = @()
Get-Content -LiteralPath $envPath | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith('#')) { return }
    $match = [regex]::Match($line, '^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$')
    if (-not $match.Success) { throw "Linea invalida en $($profileConfig.env_file)" }
    $name = $match.Groups[1].Value
    $value = $match.Groups[2].Value.Trim()
    if ($value.Length -ge 2 -and (($value.StartsWith('"') -and $value.EndsWith('"')) -or
                                  ($value.StartsWith("'") -and $value.EndsWith("'")))) {
        $value = $value.Substring(1, $value.Length - 2)
    }
    $original[$name] = [Environment]::GetEnvironmentVariable($name, 'Process')
    $changed += $name
    [Environment]::SetEnvironmentVariable($name, $value, 'Process')
}

try {
    & $Command[0] $Command[1..($Command.Length - 1)]
    $exitCode = $LASTEXITCODE
}
finally {
    foreach ($name in $changed) {
        [Environment]::SetEnvironmentVariable($name, $original[$name], 'Process')
    }
}
exit $exitCode
