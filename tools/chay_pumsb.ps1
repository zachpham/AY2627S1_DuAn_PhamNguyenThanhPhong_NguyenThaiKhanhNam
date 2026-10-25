# Runs the patched PHMN build on pumsb_negative at the minUtil levels of Figure 5(c)
# that have not been measured yet.
#
# The script is restartable: a level whose log already holds a finished run is skipped,
# so an interrupted session only loses the level that was in flight. Every run is teed
# to output/runs/ and one row is appended to output/do_luong.csv.
#
# Launch it detached from any terminal, so closing the terminal does not kill it.
# The project root holds a space and Vietnamese letters, which Start-Process mangles
# when -ArgumentList is an array, so pass ONE quoted string and use the 8.3 short path:
#
#   $fso = New-Object -ComObject Scripting.FileSystemObject
#   $short = $fso.GetFile("D:\Du an CNTT\tools\chay_pumsb.ps1").ShortPath
#   Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$short`"" -WindowStyle Minimized
#
# On this machine the short path resolves to D:\DNCNTT~1\tools\CHAY_P~1.PS1.
# Re-running after an interruption is safe and costs only the level that was in flight.

# step: work from the project root, never from tools/, because SPMF needs relative paths
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# step: cheapest level first; the run cost grows fast as minUtil falls
$levels   = @(5600000, 5400000, 5200000, 5000000)
$periodic = @('1', '3000', '1', '2000')          # minPer maxPer minAvg maxAvg, Table 8
$csv_path = 'output\do_luong.csv'
$classpath = 'build/patched;tools/spmf/spmf.jar'

New-Item -ItemType Directory -Force -Path 'output\runs' | Out-Null

Write-Output "pumsb_negative, ban da sua, tham so chu ky 1-3000-1-2000"
Write-Output "so muc can chay: $($levels.Count)"
Write-Output ""

foreach ($minutil in $levels)
{
    $out_path = "output\pumsb_f_$minutil.txt"
    $log_path = "output\runs\pumsb_f_$minutil.log"

    # step: skip a level that already finished, so the script can be re-run safely
    if (Test-Path $log_path)
    {
        $old = Get-Content $log_path -Raw
        if ($old -match 'itemsets count')
        {
            Write-Output "minUtil $minutil : da xong truoc do, bo qua"
            continue
        }
        Write-Output "minUtil $minutil : log cu khong hoan chinh, chay lai"
    }

    $started = Get-Date
    Write-Output "minUtil $minutil : bat dau $($started.ToString('HH:mm:ss dd/MM'))"

    # step: run java as its own process so its CPU time can be read back. SPMF reports
    # WALL time, which a closed laptop lid inflates by the whole suspended period; CPU
    # time is immune to that, so both are recorded and CPU time is the one to trust.
    $err_path = "$log_path.err"
    $java_args = "-Xmx6g -cp `"$classpath`" ca.pfv.spmf.gui.Main run PHMN " +
                 "data/pumsb_negative.txt $out_path $minutil " +
                 "$($periodic[0]) $($periodic[1]) $($periodic[2]) $($periodic[3])"

    $proc = Start-Process -FilePath 'java' -ArgumentList $java_args `
        -WorkingDirectory $root -RedirectStandardOutput $log_path `
        -RedirectStandardError $err_path -NoNewWindow -PassThru -Wait

    $cpu_giay = [math]::Round($proc.TotalProcessorTime.TotalSeconds, 1)
    $wall_giay = [math]::Round(((Get-Date) - $started).TotalSeconds, 1)

    # step: a big gap between wall and cpu means the machine slept mid-run
    if ($wall_giay -gt ($cpu_giay * 1.5))
    {
        Write-Output "  CANH BAO: troi $wall_giay giay nhung CPU chi $cpu_giay giay"
        Write-Output "  -> may da ngu giua lan chay, con so Time cua SPMF KHONG dung duoc"
    }

    $text = Get-Content $log_path -Raw

    # step: pull the four reported numbers back out of the console text
    $mau      = [regex]::Match($text, 'itemsets count : (\d+)')
    $ung_vien = [regex]::Match($text, 'Candidate count : (\d+)')
    $thoi_gian = [regex]::Match($text, 'Time : ([\d.]+)')
    $bo_nho   = [regex]::Match($text, 'Memory ~ ([\d.]+)')

    if (-not $mau.Success)
    {
        Write-Output "minUtil $minutil : KHONG XONG, xem $log_path"
        continue
    }

    $v_mau = $mau.Groups[1].Value
    $v_ung_vien = $ung_vien.Groups[1].Value
    $v_thoi_gian = $thoi_gian.Groups[1].Value
    $v_bo_nho = $bo_nho.Groups[1].Value
    $ngay = (Get-Date).ToString('yyyy-MM-dd')

    $row = "pumsb,da_sua,$minutil,1,3000,1,2000,$v_mau,$v_ung_vien,$v_thoi_gian,$v_bo_nho,$out_path,$log_path,$ngay,,$cpu_giay"
    # step: ascii on purpose, every value is a number or a path; utf8 here would
    # append a byte-order mark into the middle of the csv on Windows PowerShell 5.1
    Add-Content -Path $csv_path -Value $row -Encoding ascii

    $phut = [math]::Round($cpu_giay / 60.0, 1)
    Write-Output "minUtil $minutil : $v_mau mau, $v_ung_vien ung vien, $phut phut CPU, $v_bo_nho MB"
    Write-Output ""
}

Write-Output "Xong het. Ket qua o $csv_path"
