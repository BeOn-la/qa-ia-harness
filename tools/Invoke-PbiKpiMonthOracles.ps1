[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('local', 'staging', 'production')]
    [string]$Profile,

    [string]$KpiId,

    [string]$Board,

    [string]$Ref
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$argsList = @(
    'pbi-kpi-month',
    '--profile', $Profile,
    '--harness-root', $root
)
if ($Board -and $Ref) {
    throw 'Usar solo -Board o -Ref, no ambos.'
}
if ($Board) {
    $argsList += @('--board', $Board)
}
if ($Ref) {
    $argsList += @('--ref', $Ref)
}
if ($KpiId) {
    $argsList += @('--kpi', $KpiId)
}

$harnessExe = Join-Path $root '.venv\Scripts\qa-harness.exe'
if (Test-Path -LiteralPath $harnessExe) {
    $cmd = @($harnessExe) + $argsList
} else {
    $python = Join-Path $root '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python)) {
        throw 'Instalar el harness: python -m pip install . (desde la raíz del repo)'
    }
    $cmd = @($python, '-m', 'qa_harness') + $argsList
}
& (Join-Path $root 'tools\Invoke-QAProfile.ps1') -Profile $Profile -Command $cmd
exit $LASTEXITCODE
