# Streamlit Cloud 업로드용 파일 묶음 생성
$root = $PSScriptRoot
$dest = Join-Path $root "goksori-cloud-bundle"
$files = @(
    "app.py",
    "member_auth.py",
    "stock_votes.py",
    "vote_settlement.py",
    "member_profile.py",
    "accuracy_badge.py",
    "cpr_room.py",
    "betting_ui.py",
    "stock_config.py",
    "naver_scraper.py",
    "toss_scraper.py",
    "backtest_core.py",
    "naver_price.py",
    "toss_price.py",
    "sentiment_core.py",
    "http_client.py",
    "requirements.txt",
    "check_cloud_deploy.py"
)

New-Item -ItemType Directory -Force -Path $dest | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $dest ".streamlit") | Out-Null

foreach ($f in $files) {
    $src = Join-Path $root $f
    if (Test-Path $src) {
        Copy-Item -Force $src (Join-Path $dest $f)
        Write-Host "copied $f"
    } else {
        Write-Warning "missing $f"
    }
}

$config = Join-Path $root ".streamlit\config.toml"
if (Test-Path $config) {
    Copy-Item -Force $config (Join-Path $dest ".streamlit\config.toml")
}

Write-Host "`nBundle ready: $dest"
Write-Host "GitHub goksori-app 저장소에 이 폴더 내용을 통째로 업로드하세요."
