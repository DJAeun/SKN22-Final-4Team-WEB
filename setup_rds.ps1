# setup_rds.ps1
# ─────────────────────────────────────────────────────────────────────────────
# AWS CLI를 사용하여 하리 페르소나 RAG용 RDS PostgreSQL 인스턴스를 자동으로 생성합니다.
# ─────────────────────────────────────────────────────────────────────────────

Write-Host "▶ AWS RDS PostgreSQL 인스턴스 생성 중..." -ForegroundColor Cyan

# 인스턴스 존재 여부 먼저 확인
$exists = aws rds describe-db-instances --region ap-northeast-2 --db-instance-identifier hari-persona-db 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ DB 인스턴스 'hari-persona-db'가 이미 존재하거나 생성 중입니다. (생성 요청 생략)" -ForegroundColor Green
} else {
    # aws.exe로 전달할 명령어를 단일 문자열로 구성 (PowerShell 인자 파싱 오류 방지)
    $createCmd = "aws rds create-db-instance " +
        "--region ap-northeast-2 " +
        "--db-instance-identifier hari-persona-db " +
        "--db-instance-class db.t3.micro " +
        "--engine postgres " +
        "--engine-version 16.6 " +
        "--master-username hari " +
        "--master-user-password murhek-vymJem-4siwra " +
        "--db-name hari_persona " +
        "--allocated-storage 20 " +
        "--publicly-accessible " +
        "--no-multi-az " +
        "--storage-type gp2 " +
        "--backup-retention-period 1"

    Write-Host "> $createCmd" -ForegroundColor DarkGray
    Invoke-Expression $createCmd

    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ RDS 생성 실패" -ForegroundColor Red
        exit 1
    }

    Write-Host "✓ RDS 인스턴스 생성 요청 완료. 프로비저닝에 약 5~10분 소요됩니다." -ForegroundColor Green
}
Write-Host ""
Write-Host "▶ 인스턴스가 'available' 상태가 될 때까지 대기 중... (최대 10분)" -ForegroundColor Cyan

$waitCmd = "aws rds wait db-instance-available --region ap-northeast-2 --db-instance-identifier hari-persona-db"
Invoke-Expression $waitCmd

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ 대기 중 오류가 발생했습니다. AWS 콘솔에서 상태를 확인하세요." -ForegroundColor Red
    exit 1
}

# Endpoint 조회
Write-Host "▶ Endpoint 정보 조회 중..." -ForegroundColor Cyan
$endpoint = (aws rds describe-db-instances --region ap-northeast-2 --db-instance-identifier hari-persona-db --query "DBInstances[0].Endpoint.Address" --output text 2>&1).Trim()

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "✓ RDS 인스턴스가 준비되었습니다!" -ForegroundColor Green
Write-Host ""
Write-Host "  Endpoint : $endpoint"
Write-Host "  Port     : 5432"
Write-Host "  DB Name  : hari_persona"
Write-Host "  User     : hari"
Write-Host ""
Write-Host "⚠ 반드시 확인하세요: RDS 보안 그룹에서 나의 PC IP(포트 5432)를 인바운드 허용해야 합니다." -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green

$envPath = Join-Path $PSScriptRoot ".env"
Read-Host "▶ 엔터키를 누르면 .env 파일에 DB_HOST 주소를 자동 업데이트합니다."
if (Test-Path $envPath) {
    (Get-Content $envPath) -replace "DB_HOST=.*", "DB_HOST=$endpoint" | Set-Content $envPath
    Write-Host "✓ .env 업뎃 완료: DB_HOST=$endpoint" -ForegroundColor Green
} else {
    Write-Host "  .env 파일을 찾을 수 없습니다. 직접 입력해주세요." -ForegroundColor Yellow
}
