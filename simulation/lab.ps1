# Single-command controls for the CloudPulse failure-simulation lab.
# Usage: ./simulation/lab.ps1 <up|down|reset|healthy|unhealthy|stop-app|start-app>
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("up", "down", "reset", "healthy", "unhealthy", "stop-app", "start-app")]
    [string]$Action
)

Set-Location (Join-Path $PSScriptRoot "..")

switch ($Action) {
    "up"        { docker compose up --build -d }
    "down"      { docker compose down --remove-orphans }
    "reset"     { docker compose down --remove-orphans; docker compose up --build -d }
    "healthy"   { $env:APP_MODE = "healthy"; docker compose up -d --force-recreate app }
    "unhealthy" { $env:APP_MODE = "unhealthy"; docker compose up -d --force-recreate app }
    "stop-app"  { docker compose stop app }
    "start-app" { docker compose start app }
}
