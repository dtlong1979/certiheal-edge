param([long]$Seed = 12345, [long]$Start = 0, [int]$Duration = 7200)
# RANDOM CHAOS - script MAY B. Sinh lich RANDOM giong HET ban Python (chaos_A.py) tu SEED chung.
# Thuc thi kill cho node edge-b*, log so vai tro con chay tren B (bang chung split-brain).
$ErrorActionPreference = "SilentlyContinue"
$TS = "tailscale"
$KEEP = 4; $GMIN = 45; $GMAX = 150; $HMIN = 30; $HMAX = 180
$NODES = @("edge-b","edge-b-1","edge-b-2","edge-b-3","edge-b-4","edge-b-5","edge-b-6","edge-b-7",
           "edge-b-8","edge-b-9","edge-b-10","edge-b-11","edge-b-12",
           "k3d-a-agent2-0","k3d-certiheal-agent-0","k3d-certiheal-agent-1")

$script:st = [int64]$Seed -band 2147483647
function Nxt { $script:st = ([int64]1103515245 * [int64]$script:st + [int64]12345) -band [int64]2147483647; return $script:st }
function Rint($a, $b) { return [int]($a + ((Nxt) % ($b - $a + 1))) }

function Gen-Schedule {
  $ev = New-Object System.Collections.ArrayList
  $down = @{}
  $alive = New-Object System.Collections.Generic.HashSet[string]
  foreach ($n in $NODES) { [void]$alive.Add($n) }
  $t = 120
  while ($t -lt ($Duration - 120)) {
    foreach ($n in @($down.Keys)) { if ($down[$n] -le $t) { [void]$alive.Add($n); $down.Remove($n) } }
    $t = $t + (Rint $GMIN $GMAX)
    foreach ($n in @($down.Keys)) { if ($down[$n] -le $t) { [void]$alive.Add($n); $down.Remove($n) } }
    $r = (Nxt) % 100
    if ($r -lt 55) { $k = 1 } elseif ($r -lt 85) { $k = 2 } else { $k = 3 }
    $k = [Math]::Min($k, $alive.Count - $KEEP)
    if ($k -lt 1) { continue }
    $pool = @($NODES | Where-Object { $alive.Contains($_) })
    $vics = @()
    for ($j = 0; $j -lt $k; $j++) {
      $idx = [int]((Nxt) % $pool.Count)
      $vics += $pool[$idx]
      $tmp = @(); for ($m = 0; $m -lt $pool.Count; $m++) { if ($m -ne $idx) { $tmp += $pool[$m] } }; $pool = $tmp
    }
    $hold = Rint $HMIN $HMAX
    foreach ($v in $vics) {
      [void]$ev.Add(@([int]$t, "kill", $v)); [void]$alive.Remove($v); $down[$v] = $t + $hold
      [void]$ev.Add(@([int]($t + $hold), "rejoin", $v))
    }
  }
  return @($ev | Sort-Object @{Expression = { $_[0] } }, @{Expression = { $_[2] } })
}

function ContainerOf($n) { if ($n -eq "edge-b") { return "k3s-agent-b" } else { return "k3s-$n" } }
$bAgents = @("k3s-agent-b"); 1..12 | ForEach-Object { $bAgents += "k3s-edge-b-$_" }

$SCHED = Gen-Schedule
$kills = ($SCHED | Where-Object { $_[1] -eq "kill" }).Count
Write-Host "[CHAOS-B] SEED=$Seed DURATION=${Duration}s | $($SCHED.Count) su kien ($kills kill). 10 dau (VERIFY):"
for ($i = 0; $i -lt [Math]::Min(10, $SCHED.Count); $i++) { Write-Host ("   t={0} {1} {2}" -f $SCHED[$i][0], $SCHED[$i][1], $SCHED[$i][2]) }

if ($Start -gt 0) {
  Write-Host "[CHAOS-B] cho START (con $($Start - [DateTimeOffset]::UtcNow.ToUnixTimeSeconds())s)..."
  while ([DateTimeOffset]::UtcNow.ToUnixTimeSeconds() -lt $Start) { Start-Sleep -Milliseconds 400 }
} else { Write-Host "[CHAOS-B] Start=0 -> chi in lich de VERIFY, khong chay. Truyen -Start <epoch> de chay that."; return }

Write-Host "[CHAOS-B] BAT DAU."
$fired = @{}; $log = New-Object System.Collections.ArrayList
while ($true) {
  $dt = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds() - $Start
  if ($dt -ge $Duration) { break }
  for ($i = 0; $i -lt $SCHED.Count; $i++) {
    if (-not $fired.ContainsKey($i) -and $SCHED[$i][0] -le $dt) {
      $fired[$i] = $true
      $node = $SCHED[$i][2]
      if ($node -like "edge-b*") {
        $c = ContainerOf $node
        if ($SCHED[$i][1] -eq "kill") { docker stop $c | Out-Null } else { docker start $c | Out-Null }
        Write-Host ("t+{0,5}s [{1}] {2}" -f $dt, $SCHED[$i][1].ToUpper(), $node) -ForegroundColor Yellow
      }
    }
  }
  $total = 0
  foreach ($a in $bAgents) { $total += (docker exec $a k3s crictl ps 2>$null | Select-String "busybox").Count }
  [void]$log.Add([pscustomobject]@{ t = $dt; roles_on_B = $total })
  Start-Sleep -Seconds 5
}
$out = "$env:USERPROFILE\chaos_B_log.json"
$log | ConvertTo-Json | Out-File -Encoding utf8 $out
Write-Host "=== CHAOS-B DONE === log tai $out"
