# MAY B: cd vao dung thu muc chua chaos_B.ps1 roi chay .\run_chaos_multi_B.ps1 (dung , khong phu thuoc path cung)
Set-Location $PSScriptRoot
$BASE=1789578060; $DUR=10800; $GAP=300; $i=0
foreach ($SEED in 201,202,203,204,205) {
  $ST = $BASE + $i*($DUR+$GAP)
  Write-Host "[B-WRAP] seed=$SEED START=$ST"
  .\chaos_B.ps1 -Seed $SEED -Start $ST -Duration $DUR
  $i++
}
Write-Host "[B-WRAP] ALL 5 DONE"
