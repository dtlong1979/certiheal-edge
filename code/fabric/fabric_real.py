# -*- coding: utf-8 -*-
"""
CertiHeal fabric THAT: phan manh control-plane bang docker network (khong iptables, khong admin).
Che do (doc topology tu cfg.json mount vao /app/fabric_cfg.json):
  agent   : HTTP server trong container, dang cai 'role', field-recovery qua peernet (ton trong SITE + CAP).
  central : container tren ctrlnet, poll agent, hoi phuc TAP TRUNG (agent phan manh -> timeout -> chiu).

LOCALITY: moi role thuoc 1 SITE; chi agent CUNG SITE moi dang cai duoc (mo phong data-locality edge).
  -> khi site edge bi cat khoi central, central KHONG the chuyen role sang site khac (dung locality)
     va cung khong voi toi site do -> role chet nam chet. Field trong site tu cuu.
coverage = so role co >=1 agent SONG dang cai.  CAP=b_v (certificate: het cho -> tu choi = fail-closed).
"""
import sys, os, json, time, threading, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PORT = 8080
CFG = json.load(open("/app/fabric_cfg.json")) if os.path.exists("/app/fabric_cfg.json") else {}
CAP = int(CFG.get("cap", 6))
AGENTS     = CFG.get("agents", [])              # ['fa-0','fa-1',...]
AGENT_SITE = {int(k): v for k, v in CFG.get("agent_site", {}).items()}   # aid -> site
ROLE_SITE  = {int(k): v for k, v in CFG.get("role_site", {}).items()}    # role -> site
ROLES      = sorted(ROLE_SITE.keys())

def http_get(url, timeout=1.5):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r: return json.loads(r.read().decode())
    except Exception: return None
def http_post(url, obj, timeout=1.5):
    try:
        req = urllib.request.Request(url, data=json.dumps(obj).encode(), headers={"Content-Type":"application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read().decode())
    except Exception: return None

# ---------------- AGENT ----------------
class St:
    def __init__(self, aid, field):
        self.aid=aid; self.site=AGENT_SITE.get(aid); self.field=field
        self.coord=True                         # True=CertiHeal (leader election); False=peer-heuristic (uncoordinated)
        self.hosted=set(); self.lock=threading.Lock()

def make_handler(st):
    class H(BaseHTTPRequestHandler):
        def log_message(self,*a): pass
        def _s(self,o,c=200):
            b=json.dumps(o).encode(); self.send_response(c)
            self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(b)))
            self.end_headers(); self.wfile.write(b)
        def do_GET(self):
            if self.path.startswith("/roles"):
                with st.lock: self._s({"aid":st.aid,"site":st.site,"hosted":sorted(st.hosted),"cap":CAP})
            elif self.path.startswith("/health"): self._s({"ok":True,"aid":st.aid})
            else: self._s({"err":"?"},404)
        def do_POST(self):
            n=int(self.headers.get("Content-Length","0")); body=self.rfile.read(n) if n else b"{}"
            try: obj=json.loads(body.decode() or "{}")
            except Exception: obj={}
            if self.path.startswith("/host"):
                r=obj.get("role")
                if ROLE_SITE.get(r)!=st.site: self._s({"ok":False,"wrong_site":True}); return   # LOCALITY
                with st.lock:
                    if r in st.hosted: self._s({"ok":True,"already":True})
                    elif len(st.hosted)<CAP: st.hosted.add(r); self._s({"ok":True})
                    else: self._s({"ok":False,"full":True})                                       # fail-closed
            elif self.path.startswith("/drop"):
                with st.lock: st.hosted.discard(obj.get("role")); self._s({"ok":True})
            elif self.path.startswith("/clear"):
                with st.lock: st.hosted=set(); self._s({"ok":True})
            elif self.path.startswith("/field"):
                st.field=bool(obj.get("on")); st.coord=bool(obj.get("coord",True)); self._s({"ok":True})
            else: self._s({"err":"?"},404)
    return H

def field_loop(st):
    """Phi tap trung: agent SONG co aid nho nhat trong site lam COORDINATOR cuc bo (leader election,
    KHONG can central/API). No gom tai cac peer cung site (qua peernet) va gan role thieu cho peer
    con cho (min load) qua POST /host; het cho -> de nguyen (fail-closed). 1 luot, tat dinh, nhanh."""
    my_roles=[r for r in ROLES if ROLE_SITE[r]==st.site]
    name_of={int(n.split("-")[-1]):n for n in AGENTS}
    site_aids=sorted(a for a in name_of if AGENT_SITE.get(a)==st.site)
    lower=[a for a in site_aids if a<st.aid]
    while True:
        time.sleep(1.2)
        if not st.field: continue
        # GATE nhe: coordinator = agent aid NHO NHAT con song trong site. Agent khac chi ping vai peer nho hon.
        # peer-heuristic (st.coord False): BO gate -> moi agent song tu quet+dat doc lap (khong leader, khong reservation).
        if st.coord:
            coord=True
            for a in lower:
                if http_get(f"http://{name_of[a]}:{PORT}/health",0.3) is not None: coord=False; break
            if not coord: continue
        # coordinator (hoac moi peer o che do peer) quet day du + gan role thieu (1 luot, ton trong CAP, fail-closed)
        loads={}; covered=set(); reach=[]
        with st.lock: loads[st.aid]=set(st.hosted)
        covered|=loads[st.aid]; reach.append(st.aid)
        for a in site_aids:
            if a==st.aid: continue
            d=http_get(f"http://{name_of[a]}:{PORT}/roles",0.4)
            if d is not None: loads[a]=set(d["hosted"]); covered|=loads[a]; reach.append(a)
        for r in sorted(x for x in my_roles if x not in covered):
            cand=sorted(reach,key=lambda a:len(loads[a]))
            for a in cand:
                if len(loads[a])<CAP:
                    if a==st.aid:
                        with st.lock:
                            if len(st.hosted)<CAP: st.hosted.add(r)
                        loads[a].add(r)
                    else:
                        ok=http_post(f"http://{name_of[a]}:{PORT}/host",{"role":r},0.4)
                        if ok and ok.get("ok"): loads[a].add(r)
                    break

def run_agent(aid, field):
    st=St(aid, field)
    threading.Thread(target=field_loop,args=(st,),daemon=True).start()
    print(f"[agent {aid}] up site={st.site} cap={CAP} field={field}",flush=True)
    ThreadingHTTPServer(("0.0.0.0",PORT),make_handler(st)).serve_forever()

# ---------------- CENTRAL ----------------
def run_central():
    print(f"[central] {len(AGENTS)} agent, {len(ROLES)} role",flush=True)
    while True:
        time.sleep(2)
        seen={}; covered=set()
        for n in AGENTS:
            d=http_get(f"http://{n}:{PORT}/roles")     # ctrlnet: agent phan manh -> None
            if d is not None: seen[n]=(set(d["hosted"]),len(d["hosted"]),d["site"]); covered|=set(d["hosted"])
        for r in [x for x in ROLES if x not in covered]:
            s=ROLE_SITE[r]
            for n,(hs,ld,site) in sorted(seen.items(),key=lambda kv:kv[1][1]):
                if site==s and ld<CAP:                 # LOCALITY + capacity
                    ok=http_post(f"http://{n}:{PORT}/host",{"role":r})
                    if ok and ok.get("ok"): seen[n]=(hs|{r},ld+1,site); break

if __name__=="__main__":
    m=sys.argv[1] if len(sys.argv)>1 else ""
    if m=="agent":
        import argparse; ap=argparse.ArgumentParser()
        ap.add_argument("--id",type=int,required=True); ap.add_argument("--field",default="0")
        a=ap.parse_args(sys.argv[2:]); run_agent(a.id, a.field=="1")
    elif m=="central": run_central()
    else: print("mode: agent | central")
