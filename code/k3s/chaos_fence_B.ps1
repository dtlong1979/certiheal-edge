# B-side CHAOS+FENCE, dong bo voi A qua LCG chung + START epoch.
# Thuc thi fault cho nut/cum cua B: co lap (iptables DROP toi control-plane A), tu-fence sau TTL, phuc hoi khi het han.
# Khong dieu khien cum (A la bo nao). Ghi su kien -> chaos_fence_B.csv.
#   powershell -ExecutionPolicy Bypass -File chaos_fence_B.ps1 -Seed 777 -Start <epoch> -Duration 1800
#   powershell -ExecutionPolicy Bypass -File chaos_fence_B.ps1 -Seed 777 -Verify    # in 12 su kien dau
param(
  [long]$Seed=777,
  [double]$Start=0,
  [int]$Duration=1800,
  [string]$CpIp="<CONTROL_PLANE_IP>",
  [int]$TTL=10,
  [switch]$Verify,
  [switch]$NoFence
)
$ErrorActionPreference="SilentlyContinue"
$NODES=@("k3d-a-agent2-0","k3d-certiheal-agent-0","k3d-certiheal-agent-1",
         "edge-b","edge-b-1","edge-b-2","edge-b-3","edge-b-4","edge-b-5",
         "edge-b-6","edge-b-7","edge-b-8","edge-b-9","edge-b-10","edge-b-11","edge-b-12")
$CLUSTERS=@(@(0,1,2),@(3,4,5),@(6,7,8),@(9,10,11,12),@(13,14,15))
$B_NODES=3..15; $B_CLUSTERS=@(1,2,3,4); $IPT="/bin/aux/iptables"
function Nxt([long]$s){ return ([long]1103515245*$s + 12345) -band 0x7FFFFFFF }
function Schedule([long]$seed,[int]$dur){
  $s=$seed; $t=0; $ev=@()
  while($true){
    $s=Nxt $s; $gap=20+($s%41); $t+=$gap
    if($t -ge $dur){ break }
    $s=Nxt $s; $isc=(($s%10) -lt 3)
    $scope= if($isc){"cluster"}else{"node"}
    $s=Nxt $s; $size= if($isc){5}else{16}
    $s=Nxt $s; $tgt=$s%$size
    $s=Nxt $s; $d= if($isc){45+($s%46)}else{30+($s%31)}
    $ev+=,([pscustomobject]@{t=$t;scope=$scope;target=$tgt;dur=$d})
  }
  return $ev
}
function NodesOf($e){ if($e.scope -eq "cluster"){ return $CLUSTERS[$e.target] | ForEach-Object { $NODES[$_] } } else { return @($NODES[$e.target]) } }
function BOwns($e){ if($e.scope -eq "node"){ return $B_NODES -contains $e.target } else { return $B_CLUSTERS -contains $e.target } }
function CName($n){ return "k3s-$n" }   # ten node k8s (edge-b-x) -> ten container docker (k3s-edge-b-x)
function Isolate($n){ $c=CName $n; docker exec $c $IPT -I OUTPUT -d $CpIp -j DROP 2>$null|Out-Null; docker exec $c $IPT -I INPUT -s $CpIp -j DROP 2>$null|Out-Null }
function Deisolate($n){ $c=CName $n; docker exec $c $IPT -D OUTPUT -d $CpIp -j DROP 2>$null|Out-Null; docker exec $c $IPT -D INPUT -s $CpIp -j DROP 2>$null|Out-Null }

if($Verify){
  $names=@("cA","cB1","cB2","cB3","cB4")
  foreach($e in (Schedule $Seed 1800 | Select-Object -First 12)){
    $tg= if($e.scope -eq "cluster"){"cum "+$names[$e.target]}else{$NODES[$e.target]}
    "t={0,4} {1,-7} {2,-14} dur={3}" -f $e.t,$e.scope,$tg,$e.dur
  }
  exit 0
}

$EV=Schedule $Seed $Duration
$MINE=@($EV | Where-Object { BOwns $_ })
foreach($e in $MINE){
  $e | Add-Member -NotePropertyName started -NotePropertyValue $false
  $e | Add-Member -NotePropertyName fenced  -NotePropertyValue $false
  $e | Add-Member -NotePropertyName done    -NotePropertyValue $false
  $e | Add-Member -NotePropertyName nodes   -NotePropertyValue (NodesOf $e)
  $e | Add-Member -NotePropertyName isoat   -NotePropertyValue 0.0
}
$tag= if($NoFence){"baseline"}else{"certiheal"}
Write-Host "[FENCE-B] mode=$tag $($EV.Count) su kien tong, $($MINE.Count) thuoc B. CpIp=$CpIp TTL=$TTL Duration=$Duration"
$log=Join-Path $PSScriptRoot "chaos_fence_B_$tag.csv"
"epoch,t,act,scope,nodes" | Out-File $log -Encoding ascii
while([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()/1000.0 -lt $Start){ Start-Sleep -Milliseconds 300 }
Write-Host "[FENCE-B] BAT DAU"
while(([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()/1000.0 - $Start) -lt ($Duration+30)){
  $rel=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()/1000.0 - $Start
  $ep=[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
  foreach($e in $MINE){
    if((-not $e.started) -and $rel -ge $e.t){
      $e.started=$true; $e.isoat=$rel
      foreach($n in $e.nodes){ Isolate $n }
      "$ep,$([int]$rel),isolate,$($e.scope),$($e.nodes -join '|')" | Out-File $log -Append -Encoding ascii
      Write-Host ("  t+{0,5:N0} ISOLATE {1} {2}" -f $rel,$e.scope,($e.nodes -join ','))
    }
    if((-not $NoFence) -and $e.started -and (-not $e.fenced) -and (-not $e.done) -and $rel -ge ($e.isoat+$TTL)){
      $e.fenced=$true
      foreach($n in $e.nodes){ docker pause (CName $n) 2>$null|Out-Null }
      "$ep,$([int]$rel),fence,$($e.scope),$($e.nodes -join '|')" | Out-File $log -Append -Encoding ascii
      Write-Host ("  t+{0,5:N0} FENCE   {1} {2}" -f $rel,$e.scope,($e.nodes -join ','))
    }
    if($e.started -and (-not $e.done) -and $rel -ge ($e.t+$e.dur)){
      $e.done=$true
      foreach($n in $e.nodes){ if($e.fenced){ docker unpause (CName $n) 2>$null|Out-Null }; Deisolate $n }
      "$ep,$([int]$rel),recover,$($e.scope),$($e.nodes -join '|')" | Out-File $log -Append -Encoding ascii
      Write-Host ("  t+{0,5:N0} RECOVER {1} {2}" -f $rel,$e.scope,($e.nodes -join ','))
    }
  }
  Start-Sleep -Seconds 2
}
foreach($e in $MINE){ foreach($n in $e.nodes){ docker unpause (CName $n) 2>$null|Out-Null; Deisolate $n } }
Write-Host "=== FENCE-B DONE -> $log ==="
