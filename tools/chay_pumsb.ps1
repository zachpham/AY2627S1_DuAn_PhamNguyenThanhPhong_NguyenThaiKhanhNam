# Runs the corrected PHMN build on pumsb_negative at the minUtil levels of Figure 5(c),
# with the periodicity thresholds of Table 8 of the paper (1-3000-1-2000).
#
#   -ban       da_sua (default, the item order of the code), duong_truoc (positive items first)
#              or def7 (negative items first); see tools/chay_thu_tu.ps1
#   -han_chot  optional deadline 'yyyy-MM-dd HH:mm' passed to every level; a level still running
#              then is stopped and its log records the CPU time used
#
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools/chay_pumsb.ps1 -ban duong_truoc
#
# With the positive-first order all five levels take minutes, not days (Section 7.10).
# The script asks Windows to keep the machine awake while it runs.
#
# Each level is one call of tools/chay_do_luong.ps1, which measures the CPU time of the real
# JVM process, writes the console log to output/runs/ and appends one row to
# output/do_luong.csv. A level whose log already holds a finished run is skipped, so the
# script can be interrupted and started again. The logs of 5,200,000 and 5,000,000 hold a
# line that marks them as finished on purpose: those two levels need days to weeks (Section
# 7.5 of the report) and are not run; delete those two logs to run them anyway.
#
# Launch it detached from any terminal, so closing the terminal does not kill it.
# The project root holds a space and Vietnamese letters, which Start-Process mangles
# when -ArgumentList is an array, so pass ONE quoted string and use the 8.3 short path:
#
#   $fso = New-Object -ComObject Scripting.FileSystemObject
#   $short = $fso.GetFile("D:\Du an CNTT\tools\chay_pumsb.ps1").ShortPath
#   Start-Process powershell -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$short`"" -WindowStyle Minimized

param(
    [ValidateSet('da_sua', 'duong_truoc', 'def7')] [string]$ban = 'da_sua',
    [string]$han_chot = ''
)

# step: work from the project root, never from tools/, because SPMF needs relative paths
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

# step: keep the machine awake while this process lives; a suspended run gives no usable time
Add-Type -Namespace ChayPumsb -Name Power -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("kernel32.dll")]
public static extern uint SetThreadExecutionState(uint flags);
'@
# 0x80000000 continuous | 0x1 system | 0x2 display: Modern Standby ignores the system request alone
[ChayPumsb.Power]::SetThreadExecutionState([uint32]2147483648 -bor [uint32]1 -bor [uint32]2) | Out-Null

# step: cheapest level first; the run cost grows fast as minUtil falls
$levels = @(5800000, 5600000, 5400000, 5200000, 5000000)

foreach ($minutil in $levels)
{
    $extra = @()
    if ($ban -ne 'da_sua') { $extra += @('-ghi_chu', "thu tu $ban cac muc pumsb") }
    if ($han_chot -ne '') { $extra += @('-han_chot', $han_chot) }
    & powershell -NoProfile -ExecutionPolicy Bypass -File 'tools\chay_do_luong.ps1' `
        -bo pumsb -ban $ban -minutil $minutil -chu_ky '1,3000,1,2000' @extra
}

[ChayPumsb.Power]::SetThreadExecutionState([uint32]2147483648) | Out-Null    # release the request

Write-Output 'Done. Results are in output\do_luong.csv'
