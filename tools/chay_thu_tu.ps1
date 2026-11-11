# Item-order experiment: runs the corrected build under three item orders on the same
# configurations, one tools/chay_do_luong.ps1 call per run, so that every run is one row of
# output/do_luong.csv with its console log and pattern file.
#
#   da_sua       ascending TWU only, as the SPMF code             (build/patched)
#   def7         negative items first, Definition 7 of F0         (build/def7)
#   duong_truoc  positive items first, compareItems of AlgoFHN    (build/duong_truoc)
#
# The three orders run back to back inside each configuration, so that a slow period of the
# machine affects all three alike. The corrected build is run again (-chay_lai) rather than reusing
# an older row, for the same reason. Build the two variants first:
#
#   py -I tools/sinh_thu_tu.py
#   javac -nowarn -cp tools/spmf/spmf.jar -d build/def7 src/def7/ca/pfv/spmf/algorithms/frequentpatterns/phmn_plus/*.java
#   javac -nowarn -cp tools/spmf/spmf.jar -d build/duong_truoc src/duong_truoc/ca/pfv/spmf/algorithms/frequentpatterns/phmn_plus/*.java
#
# Usage, from the project root:
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools/chay_thu_tu.ps1
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools/chay_thu_tu.ps1 -pumsb -han_chot "2026-11-10 06:45"
#
#   -pumsb     run pumsb_negative at 5,800,000 ONLY, instead of the four small configurations.
#              The corrected build alone takes 2.5 to 3.7 hours there, so the cheapest order runs
#              first and the order of Definition 7, expected to be the slowest, runs last
#   -accidents run accidents_negative at the five levels of Figure 5(a) ONLY, with the positive-first
#              order and the order of the code, both run afresh (-chay_lai) in one session, so that
#              the comparison with Figure 5(a) uses runs of the same day. The rows get their own
#              ghi_chu, so the comparison of Table 7.17 (analysis/so_thu_tu.py) is not affected
#   -han_chot  deadline 'yyyy-MM-dd HH:mm' passed to the order of Definition 7 only: if it is still
#              running then, it is stopped and its log records the CPU time used, a lower bound
#
# While it runs, the script asks Windows to keep the machine and the display awake
# (SetThreadExecutionState); the request ends with the script. The power settings themselves are not
# changed. On a machine with Modern Standby the display request is what prevents the idle standby;
# closing the lid or pressing the power button still suspends the machine.
#
# Then compare the outputs and print the table: py -I analysis/so_thu_tu.py

param(
    [switch]$pumsb,
    [switch]$accidents,
    [string]$han_chot = ''
)

# step: work from the project root, never from tools/, because SPMF needs relative paths
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

foreach ($bt in @('patched', 'def7', 'duong_truoc'))
{
    if (-not (Test-Path "build/$bt/ca/pfv/spmf/algorithms/frequentpatterns/phmn_plus/AlgoPHMN.class"))
    {
        Write-Output "build/$bt is missing; see the header of this script"
        exit 1
    }
}

# step: keep the machine awake while this process lives; a suspended run gives no usable time
Add-Type -Namespace ThuTu -Name Power -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("kernel32.dll")]
public static extern uint SetThreadExecutionState(uint flags);
'@
$ES_CONTINUOUS      = [uint32]2147483648                           # 0x80000000
$ES_SYSTEM_REQUIRED = [uint32]1
$ES_DISPLAY_REQUIRED = [uint32]2                               # Modern Standby ignores SYSTEM alone
[ThuTu.Power]::SetThreadExecutionState($ES_CONTINUOUS -bor $ES_SYSTEM_REQUIRED -bor $ES_DISPLAY_REQUIRED) | Out-Null

# step: cheapest configuration first; every one uses minPer = 1
$note = 'thi nghiem thu tu muc'
$fresh_all = $false
if ($accidents)
{
    $configurations = @()
    foreach ($m in @(19000000, 18000000, 17000000, 15000000, 13000000))
    {
        $configurations += @{ bo = 'accidents'; minutil = $m; chu_ky = '1,2000,5,1000' }   # Table 8 of F0
    }
    $orders = @('duong_truoc', 'da_sua')
    $note = 'thu tu muc accidents nam muc'
    $fresh_all = $true
}
elseif ($pumsb)
{
    $configurations = @(
        @{ bo = 'pumsb'; minutil = 5800000; chu_ky = '1,3000,1,2000' }      # Table 8 of F0
    )
    $orders = @('duong_truoc', 'da_sua', 'def7')
}
else
{
    $configurations = @(
        @{ bo = 'chess';     minutil = 150000;   chu_ky = '1,3196,1,3196' },   # loose, as Section 7.3
        @{ bo = 'mushroom';  minutil = 100000;   chu_ky = '1,3000,1,2000' },   # as E8 at maxAvg 2000
        @{ bo = 'accidents'; minutil = 19000000; chu_ky = '1,2000,5,1000' },   # Table 8 of F0
        @{ bo = 'accidents'; minutil = 13000000; chu_ky = '1,2000,5,1000' }    # Table 8 of F0
    )
    $orders = @('da_sua', 'def7', 'duong_truoc')
}

foreach ($c in $configurations)
{
    foreach ($ban in $orders)
    {
        $extra = @('-ghi_chu', $note)
        if ($ban -eq 'da_sua' -or $fresh_all) { $extra += '-chay_lai' } # a fresh run in this session
        if ($ban -eq 'def7' -and $han_chot -ne '') { $extra += @('-han_chot', $han_chot) }
        & powershell -NoProfile -ExecutionPolicy Bypass -File 'tools\chay_do_luong.ps1' `
            -bo $c.bo -ban $ban -minutil $c.minutil -chu_ky $c.chu_ky @extra
    }
}

[ThuTu.Power]::SetThreadExecutionState($ES_CONTINUOUS) | Out-Null    # release the request
Write-Output "Done $((Get-Date).ToString('HH:mm:ss dd/MM')). Compare with: py -I analysis/so_thu_tu.py"
