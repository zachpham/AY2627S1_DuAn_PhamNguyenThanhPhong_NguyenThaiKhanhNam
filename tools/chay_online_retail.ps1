# Real-data case study (Section 7.12 of the report): runs PHMN on online_retail_negative under three
# periodicity settings, several minUtil levels and four builds, one tools/chay_do_luong.ps1 call per
# run, so that every run is one row of output/do_luong.csv with its console log and pattern file.
#
#   weekly    1,700,1,350      bought again within about two weeks (700 customer-weeks) and about
#                              once a week on average (avgPer <= 350); 335 transactions make a week
#   loose     1,3000,1,3000    within about nine weeks, and nine weeks on average
#   none      1,17780,1,17780  no periodicity constraint at all (|D| = 17,780)
#
# The four builds run back to back inside each configuration: cong_bo (published), da_sua (patched),
# def7 and duong_truoc (the two item-order variants of Section 7.10). Build the variants first, as in
# README section 5. Every run gets a deadline ten minutes after it starts: without a periodicity
# constraint the output grows exponentially below 7,000,000, which is why the grid stops there.
#
# Build the database first, then run, then check every output:
#   py -I tools/sinh_online_retail.py > output/runs/sinh_online_retail.log
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools/chay_online_retail.ps1
#   py -I analysis/so_online_retail.py

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$grid = @(
    @{ chu_ky = '1,700,1,350';     muc = @(5000000, 2000000, 1000000, 500000, 200000, 100000) },
    @{ chu_ky = '1,3000,1,3000';   muc = @(5000000, 2000000, 1000000) },
    @{ chu_ky = '1,17780,1,17780'; muc = @(10000000, 9000000, 8000000, 7000000) }
)
$builds = @('cong_bo', 'da_sua', 'def7', 'duong_truoc')

foreach ($setting in $grid)
{
    foreach ($min_util in $setting.muc)
    {
        foreach ($build in $builds)
        {
            # step: a deadline per run, so a runaway configuration cannot fill the disk
            $deadline = (Get-Date).AddMinutes(10).ToString('yyyy-MM-dd HH:mm')
            & powershell -NoProfile -ExecutionPolicy Bypass -File 'tools\chay_do_luong.ps1' `
                -bo online_retail -ban $build -minutil $min_util -chu_ky $setting.chu_ky `
                -ghi_chu 'online retail' -han_chot $deadline
        }
    }
}
