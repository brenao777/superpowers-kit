param(
    [Parameter(Position = 0, Mandatory = $true)]
    [ValidateSet("list", "check", "install", "summary")]
    [string]$Action,

    [Parameter(Position = 1)]
    [string]$Component = ""
)

$Components = @(
    [pscustomobject]@{ Id = "winget"; Name = "winget"; Group = "базовый"; Command = "winget"; Package = "" },
    [pscustomobject]@{ Id = "git"; Name = "Git"; Group = "базовый"; Command = "git"; Package = "Git.Git" },
    [pscustomobject]@{ Id = "node"; Name = "Node.js и npm"; Group = "базовый"; Command = "node"; Package = "OpenJS.NodeJS.LTS" },
    [pscustomobject]@{ Id = "python"; Name = "Python"; Group = "базовый"; Command = "python"; Package = "Python.Python.3.13" },
    [pscustomobject]@{ Id = "uv"; Name = "uv"; Group = "базовый"; Command = "uv"; Package = "astral-sh.uv" },
    [pscustomobject]@{ Id = "ripgrep"; Name = "ripgrep (rg)"; Group = "базовый"; Command = "rg"; Package = "BurntSushi.ripgrep.MSVC" },
    [pscustomobject]@{ Id = "jq"; Name = "jq"; Group = "базовый"; Command = "jq"; Package = "jqlang.jq" },
    [pscustomobject]@{ Id = "curl"; Name = "curl"; Group = "базовый"; Command = "curl.exe"; Package = "cURL.cURL" },
    [pscustomobject]@{ Id = "docker"; Name = "Docker Desktop"; Group = "расширенный"; Command = "docker"; Package = "Docker.DockerDesktop" },
    [pscustomobject]@{ Id = "gh"; Name = "GitHub CLI"; Group = "расширенный"; Command = "gh"; Package = "GitHub.cli" },
    [pscustomobject]@{ Id = "pnpm"; Name = "pnpm"; Group = "расширенный"; Command = "pnpm"; Package = "npm:pnpm" },
    [pscustomobject]@{ Id = "yarn"; Name = "Yarn"; Group = "расширенный"; Command = "yarn"; Package = "npm:yarn" },
    [pscustomobject]@{ Id = "bun"; Name = "Bun"; Group = "расширенный"; Command = "bun"; Package = "npm:bun" },
    [pscustomobject]@{ Id = "ffmpeg"; Name = "FFmpeg"; Group = "расширенный"; Command = "ffmpeg"; Package = "Gyan.FFmpeg" },
    [pscustomobject]@{ Id = "go"; Name = "Go"; Group = "расширенный"; Command = "go"; Package = "GoLang.Go" },
    [pscustomobject]@{ Id = "deno"; Name = "Deno"; Group = "расширенный"; Command = "deno"; Package = "DenoLand.Deno" }
)

function Get-ItemById([string]$Id) {
    return $Components | Where-Object { $_.Id -eq $Id } | Select-Object -First 1
}

function Test-Ready($Item) {
    if (Get-Command $Item.Command -ErrorAction SilentlyContinue) { return $true }
    if ($Item.Id -eq "docker") {
        $DockerCli = Join-Path $env:ProgramFiles "Docker\Docker\resources\bin\docker.exe"
        $DockerApp = Join-Path $env:ProgramFiles "Docker\Docker\Docker Desktop.exe"
        return ((Test-Path $DockerCli) -or (Test-Path $DockerApp))
    }
    return $false
}

function Get-VersionText($Item) {
    if ($Item.Id -eq "winget") { return (& winget --version 2>$null | Select-Object -First 1) }
    if ($Item.Id -eq "python") { return (& python --version 2>&1 | Select-Object -First 1) }
    if ($Item.Id -eq "ffmpeg") { return (& ffmpeg -version 2>&1 | Select-Object -First 1) }
    if ($Item.Id -eq "go") { return (& go version 2>&1 | Select-Object -First 1) }
    if ($Item.Id -eq "docker" -and -not (Get-Command docker -ErrorAction SilentlyContinue)) {
        return "приложение установлено, нужен первый запуск"
    }
    $Command = $Item.Command
    return (& $Command --version 2>&1 | Select-Object -First 1)
}

function Get-Hint([string]$Id) {
    switch ($Id) {
        "winget" { return "Обновите приложение App Installer в Microsoft Store и снова откройте PowerShell." }
        { $_ -in @("pnpm", "yarn") } { return "Проверьте Node.js и npm, снова откройте PowerShell и повторите этап." }
        "docker" { return "Откройте Docker Desktop, пройдите первый запуск и дождитесь готовности приложения." }
        default { return "Проверьте интернет и winget, выполните winget source update и повторите этот этап." }
    }
}

function Install-Item($Item) {
    if ($Item.Id -eq "winget") {
        Write-Output "winget устанавливается вместе с App Installer. Откройте Microsoft Store и обновите App Installer."
        return 30
    }

    if ($Item.Package.StartsWith("npm:")) {
        if (-not (Get-Command npm.cmd -ErrorAction SilentlyContinue)) {
            Write-Output "Сначала требуется Node.js и npm."
            return 20
        }
        $NpmPackage = $Item.Package.Substring(4)
        & npm.cmd install -g $NpmPackage
        if ($LASTEXITCODE -ne 0) { return 20 }
        return 0
    }

    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        Write-Output "Сначала требуется winget."
        return 20
    }

    & winget install --id $Item.Package --exact --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { return 20 }
    return 0
}

function Show-Check($Item) {
    if (Test-Ready $Item) {
        Write-Output "READY|$($Item.Id)|$($Item.Name)|$(Get-VersionText $Item)"
        return 0
    }
    Write-Output "MISSING|$($Item.Id)|$($Item.Name)|$(Get-Hint $Item.Id)"
    return 10
}

if ($Action -eq "list") {
    $Components | Select-Object @{Name="ID";Expression={$_.Id}}, @{Name="ИНСТРУМЕНТ";Expression={$_.Name}}, @{Name="ГРУППА";Expression={$_.Group}} | Format-Table -AutoSize
    exit 0
}

if ($Action -eq "summary") {
    $Rows = foreach ($Item in $Components) {
        if (Test-Ready $Item) {
            [pscustomobject]@{ ИНСТРУМЕНТ = $Item.Name; СТАТУС = "готово"; ПОДРОБНОСТИ = Get-VersionText $Item }
        } else {
            [pscustomobject]@{ ИНСТРУМЕНТ = $Item.Name; СТАТУС = "требует внимания"; ПОДРОБНОСТИ = Get-Hint $Item.Id }
        }
    }
    $Rows | Format-Table -AutoSize -Wrap
    if ($Rows.СТАТУС -contains "требует внимания") { exit 10 }
    exit 0
}

$Item = Get-ItemById $Component
if (-not $Item) {
    Write-Output "Неизвестный компонент: $Component"
    exit 20
}

if ($Action -eq "check") {
    $Code = Show-Check $Item
    exit $Code
}

if (Test-Ready $Item) {
    Write-Output "SKIPPED|$($Item.Id)|$($Item.Name)|уже установлено"
    exit 0
}

Write-Output "INSTALLING|$($Item.Id)|$($Item.Name)"
$InstallCode = Install-Item $Item
if ($InstallCode -eq 30) {
    Write-Output "ACTION_REQUIRED|$($Item.Id)|$($Item.Name)|$(Get-Hint $Item.Id)"
    exit 30
}
if ($InstallCode -ne 0) {
    Write-Output "FAILED|$($Item.Id)|$($Item.Name)|$(Get-Hint $Item.Id)"
    exit 20
}

$CheckCode = Show-Check $Item
if ($CheckCode -ne 0) {
    Write-Output "ACTION_REQUIRED|$($Item.Id)|$($Item.Name)|Снова откройте PowerShell и повторите проверку."
    exit 30
}
exit 0
