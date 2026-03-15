param(
    [string]$InstallDir = "$env:USERPROFILE\\SillyTavern",
    [string]$BridgeEnv = "$env:USERPROFILE\\.codex\\sillytavern-codex-bridge.env",
    [string]$BridgeWorkspace = "$env:USERPROFILE\\.codex\\tmp\\sillytavern-bridge-workspace",
    [int]$BridgePort = 8787,
    [string]$ApiKey = ""
)

$ErrorActionPreference = "Stop"

function Assert-Command {
    param([string]$Name)
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "Missing required command: $Name"
    }
}

Assert-Command git
Assert-Command node
Assert-Command npm
Assert-Command python
Assert-Command codex

$codexCommand = Get-Command codex.cmd -ErrorAction SilentlyContinue
if (-not $codexCommand) {
    $codexCommand = Get-Command codex -ErrorAction Stop
}
$codexBin = $codexCommand.Source

if (-not (Test-Path $InstallDir)) {
    git clone https://github.com/SillyTavern/SillyTavern.git $InstallDir
}

npm install --prefix $InstallDir

New-Item -ItemType Directory -Force -Path $BridgeWorkspace | Out-Null
New-Item -ItemType Directory -Force -Path ([System.IO.Path]::GetDirectoryName($BridgeEnv)) | Out-Null

if (-not $ApiKey) {
    $ApiKey = [guid]::NewGuid().ToString("N")
}

$envContent = @(
    "SILLYTAVERN_CODEX_HOST=127.0.0.1"
    "SILLYTAVERN_CODEX_PORT=$BridgePort"
    "SILLYTAVERN_CODEX_API_KEY=$ApiKey"
    "SILLYTAVERN_CODEX_MODEL_ID=codex-cli"
    "SILLYTAVERN_CODEX_BIN=$codexBin"
    "SILLYTAVERN_CODEX_CWD=$BridgeWorkspace"
    "SILLYTAVERN_CODEX_TIMEOUT=600"
)
Set-Content -Path $BridgeEnv -Value $envContent -Encoding UTF8

$settingsPath = Join-Path $InstallDir 'data\\default-user\\settings.json'
$presetPath = Join-Path $InstallDir 'data\\default-user\\OpenAI Settings\\Default.json'
$secretsPath = Join-Path $InstallDir 'data\\default-user\\secrets.json'

if (Test-Path $settingsPath) {
    $settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
    $settings.main_api = 'openai'
    $settings.power_user.auto_connect = $true
    $settings.oai_settings.chat_completion_source = 'custom'
    $settings.oai_settings.custom_model = 'codex-cli'
    $settings.oai_settings.custom_url = "http://127.0.0.1:$BridgePort/v1"
    $settings | ConvertTo-Json -Depth 100 | Set-Content -Path $settingsPath -Encoding UTF8
}

if (Test-Path $presetPath) {
    $preset = Get-Content $presetPath -Raw | ConvertFrom-Json
    $preset.chat_completion_source = 'custom'
    $preset.custom_model = 'codex-cli'
    $preset.custom_url = "http://127.0.0.1:$BridgePort/v1"
    $preset | ConvertTo-Json -Depth 100 | Set-Content -Path $presetPath -Encoding UTF8
}

$secretPayload = @{
    api_key_custom = @(
        @{
            id = [guid]::NewGuid().ToString()
            value = $ApiKey
            label = 'Codex Bridge'
            active = $true
        }
    )
}
$secretPayload | ConvertTo-Json -Depth 10 | Set-Content -Path $secretsPath -Encoding UTF8

Write-Host "SillyTavern is ready at $InstallDir"
Write-Host "Bridge env file: $BridgeEnv"
Write-Host "API key: $ApiKey"
Write-Host "Base URL: http://127.0.0.1:$BridgePort/v1"
Write-Host ""
Write-Host "Next:"
Write-Host "1. powershell -ExecutionPolicy Bypass -File $PSScriptRoot\\start_bridge_windows.ps1 -EnvFile $BridgeEnv"
Write-Host "2. npm start --prefix $InstallDir"
