# Ghi lai thoi gian CPU cua moi tien trinh java, 60 giay mot lan.
#
# Ly do ton tai: con so `Time` ma SPMF in ra la thoi gian TROI, nen may ngu
# giua lan chay la no phong lên vo nghia. Thoi gian CPU cua tien trinh thi
# mien nhiem voi chuyen do. tools/chay_e8.ps1 tu doc TotalProcessorTime cua
# tien trinh con nen khong can script nay; nhung lan chay pumsb 5,4 trieu
# dang do mot ban script CU khoi chay, ban do KHONG ghi CPU. Script nay la
# luoi an toan cho lan chay do: khi tien trinh java bien mat, mau do cuoi
# cung truoc do cho biet no da dung bao nhieu giay CPU, sai so toi da 60 giay.
#
# Chay detached (duong dan du an co dau cach, xem ba cai bay trong architecture.md):
#   $fso = New-Object -ComObject Scripting.FileSystemObject
#   $short = $fso.GetFile("D:\Du an CNTT\tools\canh_cpu.ps1").ShortPath
#   Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$short`"" -WindowStyle Hidden

param(
    [int]$moi_giay = 60,
    [int]$so_gio_toi_da = 48
)

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$csv = 'output\runs\cpu_watch.csv'
if (-not (Test-Path $csv))
{
    Set-Content -Path $csv -Value 'thoi_diem,pid,bat_dau,cpu_giay,bo_nho_mb' -Encoding ascii
}

$het_han = (Get-Date).AddHours($so_gio_toi_da)

while ((Get-Date) -lt $het_han)
{
    foreach ($p in @(Get-Process java -ErrorAction SilentlyContinue))
    {
        # step: bo qua tien trinh launcher nho, chi quan tam tien trinh dang tinh
        if ($p.WorkingSet64 -lt 100MB) { continue }

        $cpu = [math]::Round($p.TotalProcessorTime.TotalSeconds, 1)
        $ram = [math]::Round($p.WorkingSet64 / 1MB, 0)
        $bd = ''
        try { $bd = $p.StartTime.ToString('yyyy-MM-dd HH:mm:ss') } catch { }
        $dong = '{0},{1},{2},{3},{4}' -f (Get-Date -Format 'yyyy-MM-dd HH:mm:ss'),
                $p.Id, $bd, $cpu, $ram
        # step: ascii co y - utf8 tren PowerShell 5.1 chen BOM vao giua file csv
        Add-Content -Path $csv -Value $dong -Encoding ascii
    }
    Start-Sleep -Seconds $moi_giay
}
