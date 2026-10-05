$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$envPath = Join-Path $projectRoot '.env'
if (Test-Path -LiteralPath $envPath) {
    exit 0
}

function New-RandomSecret([int]$byteCount) {
    $bytes = [byte[]]::new($byteCount)
    $generator = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $generator.GetBytes($bytes)
    }
    finally {
        $generator.Dispose()
    }
    return [Convert]::ToBase64String($bytes).TrimEnd('=').Replace('+', '-').Replace('/', '_')
}

$adminPassword = New-RandomSecret 24
$databasePassword = New-RandomSecret 32
$jwtSecret = New-RandomSecret 48
$contents = @(
    'POSTGRES_DB=smart_parking'
    'POSTGRES_USER=parking'
    "POSTGRES_PASSWORD=$databasePassword"
    "JWT_SECRET=$jwtSecret"
    "INITIAL_ADMIN_PASSWORD=$adminPassword"
    'VITE_API_URL=/api'
)
[System.IO.File]::WriteAllLines($envPath, $contents, [System.Text.Encoding]::ASCII)

Write-Host ''
Write-Host 'First-run administrator account (save this password securely):' -ForegroundColor Yellow
Write-Host 'Username: admin'
Write-Host "Password: $adminPassword" -ForegroundColor Green
Write-Host 'This password is shown only when the local .env file is first created.'
Write-Host ''
