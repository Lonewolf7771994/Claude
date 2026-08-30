<#
.SYNOPSIS
    Links a downloaded MCP bridge/server file to Claude Code and/or Claude Desktop on Windows.

.DESCRIPTION
    Finds the bridge file (by default it searches your Downloads folder), works out how it
    has to be launched (node / python / java / exe / .ps1 / package folder), smoke-tests it
    by speaking the MCP handshake to it over stdio, and then registers it:

      * with Claude Code  -> "claude mcp add ..."
      * with Claude Desktop -> %APPDATA%\Claude\claude_desktop_config.json (a backup is written first)

.PARAMETER Path
    The downloaded file or folder. If omitted, the script scans $HOME\Downloads for likely
    MCP bridge files and uses the match if there is exactly one.

.PARAMETER Name
    Server name to register it under. Defaults to a slug of the file name.

.PARAMETER Target
    claude-code (default), claude-desktop, or both.

.PARAMETER Scope
    Claude Code config scope: local, user (default) or project.

.PARAMETER InstallTo
    Where a .zip is unpacked to. Defaults to $HOME\.mcp-servers\<name>.

.PARAMETER EnvVar
    Environment variables for the server, e.g. -EnvVar @{ API_KEY = 'sk-...' }

.PARAMETER SkipTest
    Skip the MCP handshake smoke test.

.PARAMETER DryRun
    Print what would happen; change nothing.

.EXAMPLE
    .\Link-McpBridge.ps1

.EXAMPLE
    .\Link-McpBridge.ps1 -Path "$HOME\Downloads\mcp-bridge.js" -Name mcp-bridge -Target both

.EXAMPLE
    .\Link-McpBridge.ps1 -Path "$HOME\Downloads\bridge.zip" -EnvVar @{ BRIDGE_TOKEN = 'abc123' }
#>
[CmdletBinding()]
param(
    [string]$Path,
    [string]$Name,
    [ValidateSet('claude-code', 'claude-desktop', 'both')]
    [string]$Target = 'claude-code',
    [ValidateSet('local', 'user', 'project')]
    [string]$Scope = 'user',
    [string]$InstallTo,
    [hashtable]$EnvVar = @{},
    [switch]$SkipTest,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version 2.0

function Write-Step { param($m) Write-Host "==> $m" -ForegroundColor Cyan }
function Write-Ok   { param($m) Write-Host "  OK  $m" -ForegroundColor Green }
function Write-Warn2{ param($m) Write-Host "  !!  $m" -ForegroundColor Yellow }
function Fail       { param($m) Write-Host "  XX  $m" -ForegroundColor Red; exit 1 }

function Test-Prop {
    # StrictMode-safe "does this object have this property, and is it non-null"
    param($Object, [string]$PropertyName)
    if ($null -eq $Object) { return $false }
    $prop = $Object.PSObject.Properties[$PropertyName]
    return ($null -ne $prop -and $null -ne $prop.Value)
}

# ---------------------------------------------------------------- find the file

function Find-BridgeFile {
    $downloads = Join-Path $HOME 'Downloads'
    if (-not (Test-Path $downloads)) { Fail "No Downloads folder at $downloads. Pass -Path explicitly." }

    $exts = '.mcpb', '.dxt', '.js', '.mjs', '.cjs', '.py', '.exe', '.jar', '.zip', '.ps1'
    $candidates = Get-ChildItem -Path $downloads -File -ErrorAction SilentlyContinue |
        Where-Object { $exts -contains $_.Extension.ToLower() -and $_.Name -match 'mcp|bridge' } |
        Sort-Object LastWriteTime -Descending

    # a folder named like an mcp bridge counts too
    $dirs = Get-ChildItem -Path $downloads -Directory -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -match 'mcp|bridge' } |
        Sort-Object LastWriteTime -Descending

    $all = @($candidates) + @($dirs)

    if ($all.Count -eq 0) {
        Write-Warn2 "Nothing matching 'mcp' or 'bridge' found in $downloads. Recent downloads:"
        Get-ChildItem -Path $downloads -File -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending | Select-Object -First 15 |
            ForEach-Object { Write-Host "      $($_.Name)" }
        Fail "Re-run with -Path `"$downloads\<the file>`""
    }
    if ($all.Count -gt 1) {
        Write-Warn2 "More than one candidate found:"
        $all | ForEach-Object { Write-Host "      $($_.FullName)" }
        Fail "Re-run with -Path pointing at the one you want."
    }
    return $all[0].FullName
}

if (-not $Path) {
    Write-Step "Looking for the bridge file in $HOME\Downloads"
    $Path = Find-BridgeFile
}
$Path = (Resolve-Path -LiteralPath $Path).Path
if (-not (Test-Path -LiteralPath $Path)) { Fail "Not found: $Path" }
Write-Ok "Using $Path"

# ---------------------------------------------------------------- unpack a zip

$item = Get-Item -LiteralPath $Path
if ($item.PSIsContainer -eq $false -and $item.Extension.ToLower() -eq '.zip') {
    if (-not $Name) { $Name = [IO.Path]::GetFileNameWithoutExtension($item.Name) }
    if (-not $InstallTo) { $InstallTo = Join-Path $HOME (Join-Path '.mcp-servers' $Name) }
    Write-Step "Unpacking archive to $InstallTo"
    if (-not $DryRun) {
        if (Test-Path $InstallTo) { Remove-Item -Recurse -Force $InstallTo }
        New-Item -ItemType Directory -Force -Path $InstallTo | Out-Null
        Expand-Archive -LiteralPath $Path -DestinationPath $InstallTo -Force
        # if the zip had a single top-level folder, use that as the root
        $top = @(Get-ChildItem -Path $InstallTo)
        if ($top.Count -eq 1 -and $top[0].PSIsContainer) { $InstallTo = $top[0].FullName }
    }
    $Path = $InstallTo
    $item = Get-Item -LiteralPath $Path
    Write-Ok "Unpacked to $Path"
}

if (-not $Name) {
    $base = if ($item.PSIsContainer) { $item.Name } else { [IO.Path]::GetFileNameWithoutExtension($item.Name) }
    $Name = ($base -replace '[^A-Za-z0-9_-]', '-').Trim('-').ToLower()
}
Write-Ok "Server name: $Name"

# ---------------------------------------------------------------- resolve entry point

function Get-FolderEntry {
    param([string]$Dir)

    $pkgPath = Join-Path $Dir 'package.json'
    if (Test-Path $pkgPath) {
        $pkg = Get-Content -Raw -LiteralPath $pkgPath | ConvertFrom-Json
        $entry = $null
        if (Test-Prop $pkg 'bin') {
            if ($pkg.bin -is [string]) { $entry = $pkg.bin }
            else { $entry = ($pkg.bin.PSObject.Properties | Select-Object -First 1).Value }
        }
        if (-not $entry -and (Test-Prop $pkg 'main')) { $entry = $pkg.main }
        if (-not $entry) { $entry = 'index.js' }

        if (-not (Test-Path (Join-Path $Dir 'node_modules'))) {
            Write-Step "Installing npm dependencies in $Dir (this can take a minute)"
            if (-not $DryRun) {
                Push-Location $Dir
                try { & cmd /c 'npm install --omit=dev' | Out-Host }
                finally { Pop-Location }
            }
        }
        return (Join-Path $Dir $entry)
    }

    foreach ($guess in 'server.py', 'main.py', '__main__.py', 'index.js', 'server.js', 'dist/index.js', 'build/index.js', 'bridge.js', 'bridge.py') {
        $p = Join-Path $Dir $guess
        if (Test-Path $p) { return $p }
    }
    Fail "Could not find an entry point inside $Dir. Pass -Path <the exact script file>."
}

if ($item.PSIsContainer) {
    $entryPath = Get-FolderEntry -Dir $item.FullName
    Write-Ok "Entry point: $entryPath"
} else {
    $entryPath = $item.FullName
}

function Resolve-Exe {
    param([string[]]$Names, [string]$Hint)
    foreach ($n in $Names) {
        $c = Get-Command $n -ErrorAction SilentlyContinue
        if ($c) { return $c.Source }
    }
    Fail "$Hint is not on PATH. Install it, open a NEW PowerShell window, then re-run."
}

$ext = [IO.Path]::GetExtension($entryPath).ToLower()
switch ($ext) {
    '.mcpb' {
        Write-Warn2 "$entryPath is a Claude Desktop extension bundle (.mcpb)."
        Write-Host  "      These are not registered from PowerShell. Open Claude Desktop ->"
        Write-Host  "      Settings -> Extensions -> Advanced settings -> Install extension..., or just"
        Write-Host  "      double-click the file. Run this to reveal it:"
        Write-Host  "        explorer.exe /select,`"$entryPath`"" -ForegroundColor White
        exit 0
    }
    '.dxt' {
        Write-Warn2 "$entryPath is a .dxt bundle (the older name for .mcpb)."
        Write-Host  "      Install it from Claude Desktop -> Settings -> Extensions, or double-click it."
        Write-Host  "        explorer.exe /select,`"$entryPath`"" -ForegroundColor White
        exit 0
    }
    { $_ -in '.js', '.mjs', '.cjs' } { $cmd = Resolve-Exe @('node') 'Node.js';        $cmdArgs = @($entryPath) }
    '.py'  { $cmd = Resolve-Exe @('python', 'python3', 'py') 'Python';                $cmdArgs = @($entryPath) }
    '.jar' { $cmd = Resolve-Exe @('java') 'Java';                                     $cmdArgs = @('-jar', $entryPath) }
    '.exe' { $cmd = $entryPath;                                                       $cmdArgs = @() }
    '.ps1' { $cmd = Resolve-Exe @('powershell') 'PowerShell'
             $cmdArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $entryPath) }
    default { Fail "Don't know how to launch a '$ext' file. Supported: .js .mjs .cjs .py .jar .exe .ps1 .zip, or a folder." }
}
Write-Ok "Launch command: $cmd $($cmdArgs -join ' ')"

# ---------------------------------------------------------------- smoke test

function ConvertTo-ArgString {
    # Windows CommandLineToArgvW quoting - Windows PowerShell 5.1 has no ProcessStartInfo.ArgumentList
    param([string[]]$Arguments)
    ($Arguments | ForEach-Object {
        $a = $_ -replace '(\\*)"', '$1$1\"'
        $a = $a -replace '(\\*)$', '$1$1'
        '"' + $a + '"'
    }) -join ' '
}

function Test-McpStdio {
    param([string]$Exe, [string[]]$Arguments, [string]$WorkDir, [hashtable]$Environment, [int]$TimeoutMs = 15000)

    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $Exe
    $psi.Arguments = ConvertTo-ArgString $Arguments
    $psi.RedirectStandardInput = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    if ($WorkDir) { $psi.WorkingDirectory = $WorkDir }
    foreach ($k in $Environment.Keys) { $psi.EnvironmentVariables[$k] = [string]$Environment[$k] }

    $proc = [System.Diagnostics.Process]::Start($psi)
    try {
        $req = @{
            jsonrpc = '2.0'; id = 1; method = 'initialize'
            params  = @{
                protocolVersion = '2025-06-18'
                capabilities    = @{}
                clientInfo      = @{ name = 'Link-McpBridge'; version = '1.0.0' }
            }
        } | ConvertTo-Json -Compress -Depth 8

        $proc.StandardInput.WriteLine($req)
        $proc.StandardInput.Flush()

        $deadline = (Get-Date).AddMilliseconds($TimeoutMs)
        while ((Get-Date) -lt $deadline) {
            $task = $proc.StandardOutput.ReadLineAsync()
            $remaining = [int]([math]::Max(250, ($deadline - (Get-Date)).TotalMilliseconds))
            if (-not $task.Wait($remaining)) { break }
            $line = $task.Result
            if ($null -eq $line) { break }              # stream closed
            if ($line -notmatch '"jsonrpc"') { continue } # log noise on stdout
            if ($line -match '"result"') { return @{ ok = $true;  detail = $line } }
            if ($line -match '"error"')  { return @{ ok = $false; detail = $line } }
        }

        $err = ''
        if ($proc.HasExited) {
            $err = $proc.StandardError.ReadToEnd()
        }
        return @{ ok = $false; detail = if ($err) { $err.Trim() } else { 'no MCP response before timeout' } }
    }
    finally {
        if (-not $proc.HasExited) { $proc.Kill() }
        $proc.Dispose()
    }
}

if (-not $SkipTest -and -not $DryRun) {
    Write-Step 'Speaking the MCP handshake to the bridge'
    $res = Test-McpStdio -Exe $cmd -Arguments $cmdArgs -WorkDir (Split-Path -Parent $entryPath) -Environment $EnvVar
    if ($res.ok) {
        Write-Ok 'The bridge answered initialize - it is a working MCP stdio server.'
    } else {
        Write-Warn2 "The bridge did not answer the handshake: $($res.detail)"
        Write-Warn2 'Registering it anyway. If Claude shows it as "failed", the cause is above'
        Write-Warn2 '(commonly a missing API key - re-run with -EnvVar @{ KEY = ''value'' }).'
    }
}

# ---------------------------------------------------------------- register

$didSomething = $false

if ($Target -in @('claude-code', 'both')) {
    Write-Step "Registering with Claude Code (scope: $Scope)"
    $claude = Get-Command claude -ErrorAction SilentlyContinue
    if (-not $claude) {
        Write-Warn2 'The "claude" CLI is not on PATH; skipping Claude Code registration.'
        Write-Warn2 'Install it with:  npm install -g @anthropic-ai/claude-code'
    } else {
        $addArgs = @('mcp', 'add', $Name, '-s', $Scope)
        foreach ($k in $EnvVar.Keys) { $addArgs += @('-e', "$k=$($EnvVar[$k])") }
        $addArgs += @('--', $cmd) + $cmdArgs

        Write-Host "      claude $($addArgs -join ' ')" -ForegroundColor DarkGray
        if (-not $DryRun) {
            & claude mcp remove $Name -s $Scope 2>$null | Out-Null   # make re-runs idempotent
            & $claude.Source @addArgs | Out-Host
            if ($LASTEXITCODE -ne 0) { Fail "claude mcp add exited with $LASTEXITCODE" }
        }
        Write-Ok 'Registered with Claude Code.'
        $didSomething = $true
    }
}

if ($Target -in @('claude-desktop', 'both')) {
    Write-Step 'Registering with Claude Desktop'
    $cfgDir  = Join-Path $env:APPDATA 'Claude'
    $cfgPath = Join-Path $cfgDir 'claude_desktop_config.json'

    if (-not $DryRun) {
        New-Item -ItemType Directory -Force -Path $cfgDir | Out-Null
        if (Test-Path $cfgPath) {
            $backup = "$cfgPath.$(Get-Date -Format yyyyMMdd-HHmmss).bak"
            Copy-Item -LiteralPath $cfgPath -Destination $backup
            Write-Ok "Backed up existing config to $backup"
            $cfg = Get-Content -Raw -LiteralPath $cfgPath | ConvertFrom-Json
        } else {
            $cfg = [pscustomobject]@{}
        }

        if (-not (Test-Prop $cfg 'mcpServers')) {
            $cfg | Add-Member -NotePropertyName mcpServers -NotePropertyValue ([pscustomobject]@{}) -Force
        }

        $entry = [ordered]@{ command = $cmd; args = $cmdArgs }
        if ($EnvVar.Count -gt 0) { $entry['env'] = $EnvVar }
        $cfg.mcpServers | Add-Member -NotePropertyName $Name -NotePropertyValue ([pscustomobject]$entry) -Force

        $cfg | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath $cfgPath -Encoding UTF8
    }
    Write-Ok "Wrote $cfgPath"
    Write-Warn2 'Quit Claude Desktop completely (system tray -> Quit) and reopen it to load the server.'
    $didSomething = $true
}

if (-not $didSomething) { Fail 'Nothing was registered.' }

Write-Host ''
Write-Step 'Verify'
Write-Host '  Claude Code:     claude mcp list'
Write-Host "                   claude mcp get $Name"
Write-Host '                   (or type /mcp inside a Claude Code session)'
Write-Host '  Claude Desktop:  the server appears under the tools icon after a full restart.'
Write-Host ''
Write-Host "  To undo:         claude mcp remove $Name -s $Scope"
