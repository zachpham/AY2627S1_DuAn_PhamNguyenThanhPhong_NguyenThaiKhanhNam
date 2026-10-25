# Thi nghiem E8 - doi thu tu ap dung cac chien luoc tia.
#
# Ba bien the do tools/sinh_e8.py sinh ra va bien dich san vao build/e8_a|b|c:
#   e8_a  EUCP truoc, ESCP sau  (thu tu goc cua ban cai dat)
#   e8_b  ESCP truoc, EUCP sau  (dao lai)
#   e8_c  thu tu goc, nhung nhac hai tra cuu map...get(X.item) ra ngoai vong lap j
#
# Hai dieu can doc tu ket qua:
#   1. So ung vien PHAI y het nhau giua ba bien the. Hai bo loc la mot phep hoi
#      nen tap cap bi loai khong phu thuoc thu tu. Lech nhau la co loi.
#   2. Thoi gian khac nhau cho biet bo loc nao thuc su lam viec. Bo loc loai
#      duoc nhieu hon ma dat truoc thi bo loc sau duoc bo qua nhieu hon.
#
# Script cung doi chieu file mau sinh ra voi ket qua cua ban da sua, de chac
# chan khong bien the nao lam thay doi dau ra.
#
# Chay detached (xem ba cai bay trong architecture.md, duong dan co dau cach):
#   $fso = New-Object -ComObject Scripting.FileSystemObject
#   $short = $fso.GetFile("D:\Du an CNTT\tools\chay_e8.ps1").ShortPath
#   Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$short`" -cho_pid 17880" -WindowStyle Minimized
#
# -cho_pid la PID cua tien trinh dang chiem CPU (vi du script do pumsb). Script
# doi tien trinh do ket thuc roi moi bat dau, de hai phep do thoi gian khong
# lam nhieu nhau. Bo tham so nay thi chay ngay.

param(
    [int]$cho_pid = 0,
    [int]$cho_toi_da_phut = 1440,
    [switch]$bo_qua_pumsb
)

# step: lam viec tu goc du an, khong bao gio tu tools/, vi SPMF can duong dan tuong doi
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$csv_path = 'output\e8_do_luong.csv'
$header = 'bien_the,dataset,minUtil,minPer,maxPer,minAvg,maxAvg,nguong_support,lan,' +
          'mau,ung_vien,cap_xet,loai_eucp,loai_escp,construct_null,la_util,la_sup,' +
          'bat_bien,thoi_gian_ms,cpu_giay,bo_nho_mb,bam_mau,khop_mau,file_log,ngay'

New-Item -ItemType Directory -Force -Path 'output\runs' | Out-Null
if (-not (Test-Path $csv_path))
{
    Set-Content -Path $csv_path -Value $header -Encoding ascii
}

# ---------------------------------------------------------------- doi CPU ranh

if ($cho_pid -gt 0)
{
    Write-Output "doi tien trinh $cho_pid ket thuc truoc khi bat dau..."
    $het_han = (Get-Date).AddMinutes($cho_toi_da_phut)
    while ((Get-Date) -lt $het_han)
    {
        try { $p = Get-Process -Id $cho_pid -ErrorAction Stop }
        catch { $p = $null }
        if ($null -eq $p) { break }
        Start-Sleep -Seconds 60
    }
    # step: tien trinh java con co the song lau hon script me, doi no luon
    while ((Get-Date) -lt $het_han)
    {
        $js = @(Get-Process java -ErrorAction SilentlyContinue |
                Where-Object { $_.WorkingSet64 -gt 200MB })
        if ($js.Count -eq 0) { break }
        Start-Sleep -Seconds 60
    }
    Write-Output "CPU da ranh luc $(Get-Date -Format 'HH:mm:ss dd/MM')"
}

# ------------------------------------------------------------- bang thi nghiem

# step: re truoc, dat truoc, de co so lieu som neu phai dung giua duong.
# moi phan tu: dataset, file du lieu, minUtil, 4 tham so chu ky, so lan lap,
# va file mau cua ban da sua de doi chieu (de trong neu khong co ban chuan).
#
# Khoi mushroom la phan quan trong nhat. ESCP cat mot cap khi support cap do
# nho hon nguong = |D|/maxAvg - 1. Voi maxAvg cua bai bao (2000) va |D| = 8124
# thi nguong chi la 3,06, tuc ESCP khong bao gio cat duoc gi. Quet maxAvg giam
# dan la cach duy nhat dua ESCP vao vung no thuc su lam viec, va do la luc cau
# hoi "thu tu nao truoc" moi co nghia.
$cau_hinh = @(
    @{ ds = 'mushroom'; f = 'data/mushroom_negative.txt'; mu = 100000;
       per = @('1','3000','1','2000'); lap = 5; chuan = '' },
    @{ ds = 'mushroom'; f = 'data/mushroom_negative.txt'; mu = 100000;
       per = @('1','3000','1','100');  lap = 5; chuan = '' },
    @{ ds = 'mushroom'; f = 'data/mushroom_negative.txt'; mu = 100000;
       per = @('1','3000','1','20');   lap = 5; chuan = '' },
    @{ ds = 'mushroom'; f = 'data/mushroom_negative.txt'; mu = 100000;
       per = @('1','3000','1','10');   lap = 5; chuan = '' },
    @{ ds = 'mushroom'; f = 'data/mushroom_negative.txt'; mu = 100000;
       per = @('1','3000','1','5');    lap = 5; chuan = '' },
    @{ ds = 'accidents'; f = 'data/accidents_negative.txt'; mu = 19000000;
       per = @('1','2000','5','1000'); lap = 3;
       chuan = 'output/accidents_f_19000000.txt' },
    @{ ds = 'accidents'; f = 'data/accidents_negative.txt'; mu = 13000000;
       per = @('1','2000','5','1000'); lap = 3;
       chuan = 'output/accidents_f_13000000.txt' },
    @{ ds = 'pumsb'; f = 'data/pumsb_negative.txt'; mu = 5800000;
       per = @('1','3000','1','2000'); lap = 1;
       chuan = 'output/pumsb_f_5800000.txt' }
)

# step: -bo_qua_pumsb de danh khoi pumsb 5,8 trieu (1 lan x 3 bien the,
#       khoang 7,6 gio) cho mot lan chay rieng ban dem. Phan mushroom +
#       accidents con lai chay khoang 1,5 gio, vua du truoc khi phai gap may.
if ($bo_qua_pumsb)
{
    $cau_hinh = @($cau_hinh | Where-Object { $_.ds -ne 'pumsb' })
    Write-Output 'bo qua khoi pumsb theo tham so -bo_qua_pumsb'
}

$bien_the = @('e8_a', 'e8_b', 'e8_c')

Write-Output ""
Write-Output "E8 - doi thu tu chien luoc tia"
Write-Output "so lan chay: $(($cau_hinh | ForEach-Object { $_.lap * $bien_the.Count } | Measure-Object -Sum).Sum)"
Write-Output ""

foreach ($ch in $cau_hinh)
{
    # step: lap vong "lan" o NGOAI va "bien the" o TRONG, tuc chay xen ke
    # a,b,c roi lai a,b,c. Neu may bi chiem CPU trong luc chay thi ca ba bien
    # the chiu anh huong nhu nhau; chay het a roi moi den b thi khong.
    for ($lan = 1; $lan -le $ch.lap; $lan++)
    {
        foreach ($bt in $bien_the)
        {
            $ten = "e8_$($bt.Substring(3))_$($ch.ds)_$($ch.mu)_ma$($ch.per[3])_r$lan"
            $log_path = "output\runs\$ten.log"
            $err_path = "$log_path.err"
            $out_path = "output\$ten.txt"

            # step: bo qua lan chay da xong, de script chay lai duoc an toan
            if (Test-Path $log_path)
            {
                $cu = Get-Content $log_path -Raw
                if ($cu -match 'itemsets count')
                {
                    Write-Output "$ten : da xong truoc do, bo qua"
                    continue
                }
            }

            $classpath = "build/$bt;tools/spmf/spmf.jar"
            $java_args = "-Xmx6g -cp `"$classpath`" ca.pfv.spmf.gui.Main run PHMN " +
                         "$($ch.f) $out_path $($ch.mu) " +
                         "$($ch.per[0]) $($ch.per[1]) $($ch.per[2]) $($ch.per[3])"

            $batdau = Get-Date
            Write-Output "$ten : bat dau $($batdau.ToString('HH:mm:ss dd/MM'))"

            # step: KHONG dung -Wait o day. Start-Process -Wait tra ve mot doi
            #       tuong Process ma TotalProcessorTime luon bang 0, nen cot
            #       cpu_giay ra rong - do dung chinh la loi da lam hong dong
            #       pumsb 5,6 trieu. Thay vao do chay khong cho, roi tu lap de
            #       giu handle song va doc CPU 500 ms mot lan. Phai lay gia tri
            #       LON NHAT chu khong phai gia tri cuoi: sau khi tien trinh
            #       thoat thi doc lai co the nem loi.
            $proc = Start-Process -FilePath 'java' -ArgumentList $java_args `
                -WorkingDirectory $root -RedirectStandardOutput $log_path `
                -RedirectStandardError $err_path -NoNewWindow -PassThru

            # step: `java` trong PATH la mot shim
            #       (C:\Program Files\Common Files\Oracle\Java\javapath\java.exe):
            #       no chi khoi chay JVM that lam TIEN TRINH CON roi ngoi cho.
            #       Doc CPU cua tien trinh ta nam duoc se ra ~0,05 giay bat ke
            #       lan chay dai bao lau. Phai tim PID con roi do tien trinh do.
            #       Tim con bang CIM mot lan duy nhat, sau do dung Get-Process
            #       cho re, vi goi CIM 500 ms mot lan se tu lam nhieu phep do.
            $con_pid = 0
            $cpu_dinh = 0.0
            while (-not $proc.HasExited)
            {
                if ($con_pid -eq 0)
                {
                    $con = @(Get-CimInstance Win32_Process `
                             -Filter "ParentProcessId=$($proc.Id)" `
                             -ErrorAction SilentlyContinue)
                    if ($con.Count -gt 0) { $con_pid = $con[0].ProcessId }
                }
                if ($con_pid -gt 0)
                {
                    try
                    {
                        $pc = Get-Process -Id $con_pid -ErrorAction Stop
                        $t = $pc.TotalProcessorTime.TotalSeconds
                        if ($t -gt $cpu_dinh) { $cpu_dinh = $t }
                    }
                    catch { }
                }
                Start-Sleep -Milliseconds 500
            }
            $proc.WaitForExit()

            if ($cpu_dinh -le 0)
            {
                Write-Output "  CANH BAO: khong do duoc CPU cua tien trinh con"
            }

            $cpu_giay = [math]::Round($cpu_dinh, 1)
            $troi_giay = [math]::Round(((Get-Date) - $batdau).TotalSeconds, 1)

            # step: troi lon hon CPU nhieu nghia la may da ngu giua lan chay.
            #       Chi canh bao voi lan chay dai hon 60 giay: lan chay ngan thi
            #       phan khoi dong JVM da du lam troi gap may lan CPU.
            if ($troi_giay -gt 60 -and $troi_giay -gt ($cpu_giay * 1.5))
            {
                Write-Output "  CANH BAO: troi $troi_giay giay, CPU chi $cpu_giay giay"
                Write-Output "  -> may ngu giua lan chay, con so Time KHONG dung duoc"
            }

            $text = Get-Content $log_path -Raw
            $m_mau = [regex]::Match($text, 'itemsets count : (\d+)')
            if (-not $m_mau.Success)
            {
                Write-Output "$ten : KHONG XONG, xem $log_path"
                continue
            }

            # step: lay lai cac con so tu van ban console. Chu y Time co the ra
            # dang khoa hoc (4.76E7), nen bieu thuc phai nhan ca E va dau +
            function Lay($mau_regex)
            {
                $m = [regex]::Match($text, $mau_regex)
                if ($m.Success) { return $m.Groups[1].Value } else { return '' }
            }

            $v_mau     = Lay 'itemsets count : (\d+)'
            $v_ungvien = Lay 'Candidate count : (\d+)'
            $v_cap     = Lay 'Pairs considered : (\d+)'
            $v_eucp    = Lay 'Rejected by EUCP : (\d+)'
            $v_escp    = Lay 'Rejected by ESCP : (\d+)'
            $v_cnull   = Lay 'Construct returned null : (\d+)'
            $v_lautil  = Lay 'of which LA-prune utility : (\d+)'
            $v_lasup   = Lay 'of which LA-prune support : (\d+)'
            $v_batbien = Lay 'Invariant [^:]*: (\S+)'
            $v_time    = Lay 'Time : ([\d.]+(?:E[+\-]?\d+)?)'
            $v_bonho   = Lay 'Memory ~ ([\d.]+)'

            # step: bam SHA256 cua file mau da sap xep. Hai lan chay cho cung
            # mot bam la cho dung mot tap mau, khong can file chuan de doi chieu.
            # Sap xep truoc vi thu tu ghi ra co the khac nhau giua cac bien the.
            $bam = 'khong_co_file'
            if (Test-Path $out_path)
            {
                $dong = @(Get-Content $out_path -ErrorAction SilentlyContinue | Sort-Object)
                $tam = [System.IO.Path]::GetTempFileName()
                Set-Content -Path $tam -Value $dong -Encoding ascii
                $bam = (Get-FileHash -Path $tam -Algorithm SHA256).Hash.Substring(0, 16)
                Remove-Item $tam -Force
            }

            # step: doi chieu file mau voi ket qua cua ban da sua. Khong bien the
            # nao duoc phep lam thay doi dau ra, nen cot nay phai luon la "khop"
            $khop = 'khong_co_chuan'
            if ($ch.chuan -and (Test-Path $ch.chuan))
            {
                $a = @(Get-Content $out_path -ErrorAction SilentlyContinue | Sort-Object)
                $b = @(Get-Content $ch.chuan -ErrorAction SilentlyContinue | Sort-Object)
                if ($a.Count -ne $b.Count) { $khop = "LECH_SO_DONG_$($a.Count)_vs_$($b.Count)" }
                else
                {
                    $khop = 'khop'
                    for ($k = 0; $k -lt $a.Count; $k++)
                    {
                        if ($a[$k] -ne $b[$k]) { $khop = "LECH_DONG_$k"; break }
                    }
                }
            }

            $ngay = (Get-Date).ToString('yyyy-MM-dd')
            # step: nguong tia support la dai luong quyet dinh ESCP co lam viec
            # hay khong, nen ghi san vao so do thay vi de nguoi doc tu tinh
            $nguong = [math]::Round(8124.0 / [double]$ch.per[3] - 1, 2)
            if ($ch.ds -eq 'pumsb')     { $nguong = [math]::Round(49046.0 / [double]$ch.per[3] - 1, 2) }
            if ($ch.ds -eq 'accidents') { $nguong = [math]::Round(340183.0 / [double]$ch.per[3] - 1, 2) }
            $row = "$bt,$($ch.ds),$($ch.mu),$($ch.per[0]),$($ch.per[1]),$($ch.per[2])," +
                   "$($ch.per[3]),$nguong,$lan,$v_mau,$v_ungvien,$v_cap,$v_eucp," +
                   "$v_escp,$v_cnull,$v_lautil,$v_lasup,$v_batbien,$v_time,$cpu_giay," +
                   "$v_bonho,$bam,$khop,$log_path,$ngay"
            # step: ascii co y, moi gia tri la so hoac duong dan. utf8 o day se
            # chen mot byte-order mark vao giua file csv tren PowerShell 5.1
            Add-Content -Path $csv_path -Value $row -Encoding ascii

            Write-Output ("  $v_mau mau, $v_ungvien ung vien, EUCP loai $v_eucp, " +
                          "ESCP loai $v_escp, $cpu_giay s CPU, bat bien $v_batbien, mau $khop")
        }
    }
    Write-Output ""
}

Write-Output "Xong het E8. Ket qua o $csv_path"
