# B-side ABLATION LADDER, tu dong nhieu seed, dong bo voi A qua base_start + i*(dur+gap).
# Ladder: k8s(fence0) -> fence(1) -> reassign(1) -> full(1). B chi CO LAP + FENCE (pause) khi config bat.
#   powershell -ExecutionPolicy Bypass -File ablation_B.ps1 -BaseStart <epoch> -Dur 480 -Gap 60 -Seeds "101,102,103,104,105,106"
param(
  [double]$BaseStart,
  [int]$Dur=480,
  [int]$Gap=60,
  [string]$CpIp="<CONTROL_PLANE_IP>",
  [int]$TTL=10
)
$ErrorActionPreference="SilentlyContinue"
$NODES=@("k3d-a-agent2-0","k3d-certiheal-agent-0","k3d-certiheal-agent-1",
         "edge-b","edge-b-1","edge-b-2","edge-b-3","edge-b-4","edge-b-5",
         "edge-b-6","edge-b-7","edge-b-8","edge-b-9","edge-b-10","edge-b-11","edge-b-12")
$CLUSTERS=@(@(0,1,2),@(3,4,5),@(6,7,8),@(9,10,11,12),@(13,14,15))
$B_NODES=3..15; $B_CLUSTERS=@(1,2,3,4); $IPT="/bin/aux/iptables"
# config: name, fence(0/1)
$CFG=@(@("k8s",0),@("fence",1),@("reassign",1),@("full",1))
$SEEDS=@(101,102,103,104,105,106)      # HARDCODE - phai giong het ablation_A.py
$S=$SEEDS.Count; $N=$CFG.Count*$S
if($BaseStart -lt [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()-30){ Write-Host "CANH BAO: BaseStart da qua, cac run dau co the bi bo. Nen dung base_start tuong lai." }
function Nxt([long]$s){ return ([long]1103515245*$s + 12345) -band 0x7FFFFFFF }
function Schedule([long]$seed,[int]$dur){
  $s=$seed; $t=0; $ev=@()
  while($true){
    $s=Nxt $s; $g=20+($s%41); $t+=$g
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
function CName($n){ return "k3s-$n" }
function Isolate($n){ $c=CName $n; docker exec $c $IPT -I OUTPUT -d $CpIp -j DROP 2>$null|Out-Null; docker exec $c $IPT -I INPUT -s $CpIp -j DROP 2>$null|Out-Null }
function Deisolate($n){ $c=CName $n; docker exec $c $IPT -D OUTPUT -d $CpIp -j DROP 2>$null|Out-Null; docker exec $c $IPT -D INPUT -s $CpIp -j DROP 2>$null|Out-Null }

$totH=[math]::Round($N*($Dur+$Gap)/3600,2)
Write-Host "[ABL-B] $N runs (4 cfg x $S seed), Dur=$Dur Gap=$Gap, TONG ~${totH}h. BaseStart in $([int]($BaseStart-[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()))s"
$log=Join-Path $PSScriptRoot "ablation_B_events.csv"
"run,config,seed,epoch,t,act,scope,nodes" | Out-File $log -Encoding ascii
for($i=0;$i -lt $N;$i++){
  $cfg=$CFG[[math]::Floor($i/$S)]; $name=$cfg[0]; $FENCE=$cfg[1]; $seed=$SEEDS[$i % $S]
  $runStart=$BaseStart + $i*($Dur+$Gap)
  while([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()/1000.0 -lt $runStart){ Start-Sleep -Milliseconds 400 }
  Write-Host "[ABL-B] RUN $($i+1)/$N config=$name seed=$seed FENCE=$FENCE"
  $EV=Schedule $seed $Dur
  $MINE=@($EV | Where-Object { BOwns $_ })
  foreach($e in $MINE){
    $e | Add-Member -NotePropertyName started -NotePropertyValue $false
    $e | Add-Member -NotePropertyName fenced  -NotePropertyValue $false
    $e | Add-Member -NotePropertyName done    -NotePropertyValue $false
    $e | Add-Member -NotePropertyName nodes   -NotePropertyValue (NodesOf $e)
    $e | Add-Member -NotePropertyName isoat   -NotePropertyValue 0.0
  }
  $t0=$runStart      # dong bo voi A (A cung dung t0=run_start)
  while(([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()/1000.0 - $t0) -lt $Dur){
    $rel=[DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()/1000.0 - $t0
    $ep=[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    foreach($e in $MINE){
      if((-not $e.started) -and $rel -ge $e.t){
        $e.started=$true; $e.isoat=$rel
        foreach($n in $e.nodes){ Isolate $n }
        "$($i+1),$name,$seed,$ep,$([int]$rel),isolate,$($e.scope),$($e.nodes -join '|')" | Out-File $log -Append -Encoding ascii
      }
      if(($FENCE -eq 1) -and $e.started -and (-not $e.fenced) -and (-not $e.done) -and $rel -ge ($e.isoat+$TTL)){
        $e.fenced=$true
        foreach($n in $e.nodes){ docker pause (CName $n) 2>$null|Out-Null }
        "$($i+1),$name,$seed,$ep,$([int]$rel),fence,$($e.scope),$($e.nodes -join '|')" | Out-File $log -Append -Encoding ascii
      }
      if($e.started -and (-not $e.done) -and $rel -ge ($e.t+$e.dur)){
        $e.done=$true
        foreach($n in $e.nodes){ if($e.fenced){ docker unpause (CName $n) 2>$null|Out-Null }; Deisolate $n }
        "$($i+1),$name,$seed,$ep,$([int]$rel),recover,$($e.scope),$($e.nodes -join '|')" | Out-File $log -Append -Encoding ascii
      }
    }
    Start-Sleep -Seconds 2
  }
  foreach($e in $MINE){ foreach($n in $e.nodes){ docker unpause (CName $n) 2>$null|Out-Null; Deisolate $n } }
  Write-Host "[ABL-B] done run $($i+1): $name seed=$seed"
}
Write-Host "=== ABL-B ALL DONE ==="
