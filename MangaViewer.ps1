# manga_viewer.ps1
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

# 获取配置文件路径（假设与脚本同目录）
$configPath = Join-Path $PSScriptRoot "config.json"

# 检查配置文件是否存在
if (-not (Test-Path $configPath)) {
    Write-Host "Config file not found at $configPath. Script execution aborted."
    exit 1
}

# 读取并解析配置文件
$config = Get-Content $configPath -Raw | ConvertFrom-Json

# 设置工作目录
Set-Location $config.script_path

# 设置Python环境
$pythonExe = $config.python_executable
$env:PYTHONPATH = $config.script_path
$env:PYTHONUNBUFFERED = '1'
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

# 1. 检查是否需要更新
& $pythonExe pre_start.py

# 2. 启动Flask服务（带配置参数）
Start-Process $pythonExe -ArgumentList "app.py", "--host", $config.app_host, "--port", $config.app_port -NoNewWindow

Start-Sleep -Seconds 2

# 3. 使用配置中的端口打开浏览器
Start-Process "microsoft-edge:http://127.0.0.1:$($config.app_port)/"