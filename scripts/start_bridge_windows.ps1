param(
    [string]$EnvFile = "$env:USERPROFILE\\.codex\\sillytavern-codex-bridge.env"
)

$ErrorActionPreference = "Stop"
$bridgeScript = Join-Path $PSScriptRoot "codex_openai_bridge.py"

if (-not (Test-Path $EnvFile)) {
    throw "Missing bridge env file: $EnvFile"
}

python $bridgeScript --env-file $EnvFile
