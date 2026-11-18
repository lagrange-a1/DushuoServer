# publish-upload.ps1
$ErrorActionPreference = "Stop"

Write-Host "=== 构建与发布流程 ===" -ForegroundColor Cyan

# 1. 构建前检查：确认 pyproject.toml / uv.lock 没有明显问题
Write-Host "正在检查项目配置..." -ForegroundColor Yellow
uv lock --check

# 2. 构建包
Write-Host "正在执行 uv build..." -ForegroundColor Yellow
uv build

# 3. 检查构建产物
if (Get-Command twine -ErrorAction SilentlyContinue) {
    Write-Host "正在使用 twine 检查构建产物..." -ForegroundColor Yellow
    python -m twine check dist/*
}
else {
    Write-Host "未安装 twine，改为使用 uvx check-sdist" -ForegroundColor Gray
    uvx check-sdist --installer uv
}

# 4. 在隔离环境里试装 wheel，确认包能正常导入
Write-Host "正在验证包可安装性..." -ForegroundColor Yellow
$wheel = Get-ChildItem -Path dist/*.whl | Select-Object -First 1
if ($wheel) {
    $pkgName = ($wheel.BaseName -split '-')[0] -replace '-', '_'
    Write-Host "验证导入: $pkgName" -ForegroundColor Gray
    uv run --no-project --no-cache --with $wheel.FullName -- python -c "import $pkgName"
}
else {
    Write-Warning "未在 dist/ 中找到 .whl 文件，跳过导入验证"
}

Write-Host "检查完成。按任意键继续发布..." -ForegroundColor Green
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# 5. 发布
Write-Host "正在执行 uv publish..." -ForegroundColor Yellow
uv publish

Write-Host "发布完成。按任意键开始清理..." -ForegroundColor Green
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# 6. 清理构建产物
Write-Host "正在清理..." -ForegroundColor Yellow

$targets = @("build", "logs", "log", ".\.pytest_cache")

Get-ChildItem -Path . -Recurse | ForEach-Object {
    if ($_.PSIsContainer -and $_.Name -like "*.egg-info") {
        $targets += $_.FullName
    }
    elseif ($_.PSIsContainer -and $_.Name -eq "__pycache__") {
        $targets += $_.FullName
    }
    elseif (!$_.PSIsContainer -and $_.Name -like "*.spec") {
        $targets += $_.FullName
    }
}

foreach ($path in $targets) {
    if (Test-Path $path) {
        Remove-Item -Path $path -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "所有操作已完成！" -ForegroundColor Cyan
Write-Host "已保留 dist 文件以便发布发行版，按下任意键删除并退出" -ForegroundColor Yellow
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

Remove-Item -Path "dist" -Recurse -Force -ErrorAction SilentlyContinue
