# Аналог Makefile для Windows (PowerShell, Docker Desktop). Использование:
#   ./infra/scripts/dev.ps1 setup | up | migrate | seed | start | stop | test | e2e | load-test | down
param([Parameter(Mandatory = $true, Position = 0)][string]$Cmd)
$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$py = Join-Path $root ".venv\Scripts\python.exe"
$compose = @("compose", "-f", (Join-Path $root "infra\compose\docker-compose.yml"))
$run = Join-Path $root ".run"
New-Item -ItemType Directory -Force $run | Out-Null

function Start-Bg($name, $file, $argList, $cwd) {
    $p = Start-Process -FilePath $file -ArgumentList $argList -WorkingDirectory $cwd -WindowStyle Hidden -PassThru `
        -RedirectStandardOutput (Join-Path $run "$name.log") -RedirectStandardError (Join-Path $run "$name.err.log")
    Set-Content (Join-Path $run "$name.pid") $p.Id
    Write-Host "$name запущен (pid $($p.Id)), лог: .run\$name.log"
}

function Stop-Bg($name) {
    $f = Join-Path $run "$name.pid"
    if (Test-Path $f) {
        $id = [int](Get-Content $f)
        # завершаем дерево процессов (npm -> node, uvicorn reloader и т.п.)
        & taskkill /PID $id /T /F 2>$null | Out-Null
        Remove-Item $f -Force
        Write-Host "$name остановлен"
    }
}

switch ($Cmd) {
    "setup" {
        if (-not (Test-Path (Join-Path $root ".env"))) { Copy-Item (Join-Path $root ".env.example") (Join-Path $root ".env") }
        if (-not (Test-Path $py)) { py -3.13 -m venv (Join-Path $root ".venv") }
        & $py -m pip install -U pip
        & $py -m pip install -e (Join-Path $root "packages\upskill_content") -e "$root\apps\api[dev]" -e "$root\apps\sandbox-worker[dev]"
        Push-Location (Join-Path $root "apps\web"); npm ci; Pop-Location
        & $py (Join-Path $root "infra\scripts\build_images.py")
    }
    "up" {
        & docker @compose up -d --wait
        $exists = & docker @compose exec -T postgres psql -U upskill -d upskill -tAc "SELECT 1 FROM pg_database WHERE datname='upskill_test'"
        if (-not $exists) { & docker @compose exec -T postgres psql -U upskill -d upskill -c "CREATE DATABASE upskill_test" }
    }
    "down" { & docker @compose down }
    "migrate" { Push-Location (Join-Path $root "apps\api"); & $py -m alembic upgrade head; Pop-Location }
    "seed" { Push-Location (Join-Path $root "apps\api"); & $py -m app.seed; Pop-Location }
    "start" {
        Start-Bg "api" $py @("-m", "uvicorn", "app.main:app", "--port", "8000", "--log-level", "warning") (Join-Path $root "apps\api")
        Start-Bg "worker" $py @("-m", "worker.main") (Join-Path $root "apps\sandbox-worker")
        Start-Bg "web" "npm.cmd" @("run", "dev") (Join-Path $root "apps\web")
        Start-Sleep 8
        Write-Host "Frontend: http://localhost:5173   API/OpenAPI: http://localhost:8000/docs"
    }
    "stop" { "web", "worker", "api" | ForEach-Object { Stop-Bg $_ } }
    "test" {
        Push-Location (Join-Path $root "apps\api")
        & $py -m ruff check .; & $py -m mypy app; & $py -m pytest -q
        Set-Location (Join-Path $root "apps\sandbox-worker")
        & $py -m ruff check .; & $py -m mypy worker; & $py -m pytest -q
        Set-Location (Join-Path $root "apps\web")
        npm run lint; npm run typecheck; npm test; npm run build
        Pop-Location
    }
    "e2e" { Push-Location (Join-Path $root "apps\web"); npx playwright install chromium; npx playwright test; Pop-Location }
    "load-test" { & $py (Join-Path $root "infra\scripts\load_test.py") }
    "all" {
        # полный запуск одной командой: Docker -> БД -> миграции -> каталог -> сервисы -> браузер
        docker info *> $null
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Запускаю Docker Desktop, жду готовности..."
            $dd = Join-Path $env:LOCALAPPDATA "Programs\DockerDesktop\Docker Desktop.exe"
            if (-not (Test-Path $dd)) { $dd = "C:\Program Files\Docker\Docker\Docker Desktop.exe" }
            Start-Process $dd
            for ($i = 0; $i -lt 60; $i++) { Start-Sleep 3; docker info *> $null; if ($LASTEXITCODE -eq 0) { break } }
            if ($LASTEXITCODE -ne 0) { throw "Docker не запустился. Запустите Docker Desktop вручную и повторите." }
        }
        & $PSCommandPath up
        & $PSCommandPath migrate
        & $PSCommandPath seed
        & $PSCommandPath stop
        & $PSCommandPath start
        for ($i = 0; $i -lt 30; $i++) {
            try { if ((Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/health/ready).StatusCode -eq 200) { break } } catch { Start-Sleep 1 }
        }
        Start-Process "http://localhost:5173"
        Write-Host "Готово: http://localhost:5173"
    }
    "halt" {
        & $PSCommandPath stop
        & $PSCommandPath down
        Write-Host "Приложение остановлено."
    }
    default { throw "Неизвестная команда: $Cmd" }
}
