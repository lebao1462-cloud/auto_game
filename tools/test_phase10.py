import json, os, shutil, subprocess, sys, tempfile, time
from pathlib import Path

ROOT=Path(r"D:\code\phongthan_proxy_manager")
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/"tools"))

from local_proxy_harness import ProxyServer
from profile_store import ProfileStore
from game_launcher import GameLauncher
from monitoring import MonitoringEngine
from route_guard import RouteGuard
from proxy_core import ProxyResult, test_proxy
from proxifier_router import build_profile, PROXIFIER, apply as restore_apply, enable_file_logging, _app_paths, route_proxy_target
from routing_verify import verify_all, verify_profile, LOG_FILE

DATA=ROOT/"data"
REAL=ProfileStore(DATA/"profiles.json").load()
TESTROOT=DATA/"phase10_runtime"
NETPROBE=Path(r"D:\PhongThanProfiles\ACC-01\netprobe.exe")
RESULTS={}
TEMP_PPX=[]

def record(name,ok,detail="",kind="REAL"):
    RESULTS[name]={"ok":bool(ok),"detail":detail,"kind":kind}
    print(f"{'PASS' if ok else 'FAIL'} | {name} | {kind} | {detail}")

def load_profiles(extra,name):
    ppx=TESTROOT/f"{name}.ppx"
    build_profile(REAL+extra,ppx)
    TEMP_PPX.append(ppx)
    subprocess.Popen([str(PROXIFIER),str(ppx),"silent-load"],cwd=str(PROXIFIER.parent),stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    time.sleep(1)
    return ppx

def mkprobe(name):
    d=TESTROOT/name; d.mkdir(parents=True,exist_ok=True)
    shutil.copy2(NETPROBE,d/"netprobe.exe")
    # game path in profile is a launcher-like exe only to derive directory
    launcher=d/"launcher.exe"
    shutil.copy2(NETPROBE,launcher)
    return d,launcher

def runprobe(d,timeout=20):
    r=subprocess.run([str(d/"netprobe.exe")],cwd=str(d),capture_output=True,text=True,timeout=timeout)
    return r.returncode,(r.stdout+r.stderr).strip()

def log_has(port):
    if not LOG_FILE.exists(): return False
    txt=LOG_FILE.read_text(encoding="utf-8",errors="replace")
    return f"127.0.0.1:{port}" in txt and "open through proxy" in txt

class FakeLauncher:
    def __init__(self): self.running={"X":123}; self.stopped=[]
    def status(self,n,p=""): return (n in self.running,self.running.get(n))
    def stop(self,n): self.stopped.append(n); return self.running.pop(n,None)
    def open_launcher(self,n,p): self.running[n]=456; return {"already_running":False}

servers=[]
try:
    TESTROOT.mkdir(parents=True,exist_ok=True)
    enable_file_logging()

    # 1 profile / 1 proxy: deterministic live routing through one local SOCKS5 forwarder.
    one=ProxyServer("socks").start(); servers.append(one)
    d1,l1=mkprobe("one_profile")
    p1={"name":"P10-ONE","proxy":f"socks5://127.0.0.1:{one.port}","game_path":str(l1)}
    load_profiles([p1],"one_profile")
    ec1,out1=runprobe(d1)
    hit1=log_has(one.port)
    record("1 profile / 1 proxy",ec1==0 and bool(out1) and hit1,f"exit={ec1}, ip={out1}, proxy=127.0.0.1:{one.port}")

    # 2 profile / 2 proxy: two distinct local SOCKS5 endpoints and two executable paths.
    twoa=ProxyServer("socks").start(); twob=ProxyServer("socks").start(); servers.extend([twoa,twob])
    d2a,l2a=mkprobe("two_profile_a"); d2b,l2b=mkprobe("two_profile_b")
    pp2=[
        {"name":"P10-TWO-A","proxy":f"socks5://127.0.0.1:{twoa.port}","game_path":str(l2a)},
        {"name":"P10-TWO-B","proxy":f"socks5://127.0.0.1:{twob.port}","game_path":str(l2b)},
    ]
    load_profiles(pp2,"two_profiles")
    eca,outa=runprobe(d2a); ecb,outb=runprobe(d2b)
    hit2a=log_has(twoa.port); hit2b=log_has(twob.port)
    record("2 profile / 2 proxy",eca==0 and ecb==0 and hit2a and hit2b and twoa.port!=twob.port,f"A={outa} via {twoa.port}; B={outb} via {twob.port}")

    # SOCKS5 no auth through local forwarding proxy + Proxifier.
    s=ProxyServer("socks").start(); servers.append(s)
    d,launcher=mkprobe("socks_noauth")
    p={"name":"P10-SOCKS","proxy":f"socks5://127.0.0.1:{s.port}","game_path":str(launcher)}
    load_profiles([p],"socks_noauth")
    ec,out=runprobe(d)
    record("Proxy SOCKS5 không auth",ec==0 and bool(out) and log_has(s.port),f"exit={ec}, ip={out}, port={s.port}")

    # SOCKS5 username/password through production auth bridge.
    sa=ProxyServer("socks",auth=("user","Pass123!")).start(); servers.append(sa)
    d,launcher=mkprobe("socks_auth")
    p={"name":"P10-SOCKS-AUTH","proxy":f"socks5://user:Pass123!@127.0.0.1:{sa.port}","game_path":str(launcher)}
    restore_apply(REAL+[p]); time.sleep(1)
    rt=route_proxy_target(p["proxy"])
    ec,out=runprobe(d)
    local_port=int(rt.get("connect_port",0))
    record("Proxy SOCKS5 có auth",ec==0 and bool(out) and log_has(local_port),f"exit={ec}, ip={out}, upstream={sa.port}, bridge={local_port}")
    restore_apply(REAL); time.sleep(1)

    # HTTP CONNECT proxy.
    hp=ProxyServer("http").start(); servers.append(hp)
    d,launcher=mkprobe("http_proxy")
    p={"name":"P10-HTTP","proxy":f"http://127.0.0.1:{hp.port}","game_path":str(launcher)}
    load_profiles([p],"http_proxy")
    ec,out=runprobe(d)
    record("HTTP/HTTPS proxy",ec==0 and bool(out) and log_has(hp.port),f"exit={ec}, ip={out}, port={hp.port}")

    # 5 profiles / 5 proxies: real Proxifier routing against five local SOCKS5 endpoints.
    five=[]; five_servers=[]; dirs=[]
    for i in range(5):
        ps=ProxyServer("socks").start(); servers.append(ps); five_servers.append(ps)
        d,launcher=mkprobe(f"p5_{i+1}"); dirs.append(d)
        five.append({"name":f"P10-5-{i+1}","proxy":f"socks5://127.0.0.1:{ps.port}","game_path":str(launcher)})
    load_profiles(five,"five_profiles")
    five_ok=True; details=[]
    for d,ps in zip(dirs,five_servers):
        ec,out=runprobe(d)
        hit=log_has(ps.port)
        five_ok &= (ec==0 and bool(out) and hit)
        details.append(f"{ps.port}:{ec}:{hit}")
    record("5 profile / 5 proxy",five_ok,", ".join(details))

    # Dead proxy before launch: must fail, never return direct IP.
    d,launcher=mkprobe("dead_before")
    dead_port=9
    p={"name":"P10-DEAD","proxy":f"socks5://127.0.0.1:{dead_port}","game_path":str(launcher)}
    load_profiles([p],"dead_before")
    ec,out=runprobe(d,20)
    no_ip=not any(ch.isdigit() for ch in out.splitlines()[-1:] if out)
    record("Proxy chết trước khi launch",ec!=0 and ("ERR" in out or "Unable" in out or "connect" in out.lower()),f"exit={ec}, output={out[:160]}")

    # Proxy dies while game is running: actual dummy game, then fail-closed guard stops it.
    dp=ProxyServer("socks").start(); servers.append(dp)
    dead_dir=DATA/"phase10"/"deadplay"
    profile={"name":"P10-DEADPLAY","proxy":f"socks5://127.0.0.1:{dp.port}","game_path":str(dead_dir/"launcher.exe"),"fail_closed":True,"auto_reconnect":False}
    load_profiles([profile],"dead_play")
    gst=GameLauncher(TESTROOT/"deadplay_running.json")
    gst.open_launcher(profile["name"],profile["game_path"])
    time.sleep(2)
    gst.reconcile([profile])
    before=verify_profile(profile,gst)
    dp.stop(); servers.remove(dp)
    time.sleep(1)
    guard=RouteGuard(TESTROOT/"guardlogs",retry_seconds=0)
    action=guard.observe(profile,{"status":"PROXY DOWN","detail":"test proxy stopped"},True,gst)
    alive,_=gst.status(profile["name"],profile["game_path"])
    record("Proxy chết khi đang chơi",before.get("status") in ("ROUTED","ROUTING") and action.get("action")=="STOPPED" and not alive,f"before={before.get('status')}, action={action}")

    # Proxy exit IP change event: deterministic monitoring integration test.
    mon=MonitoringEngine(TESTROOT/"monlogs")
    state={"n":0}
    mp=[{"name":"M","proxy":"socks5://fake:1"}]
    def fake(raw,timeout=4):
        return ProxyResult(raw,True,ip="10.0.0.1" if state["n"]==0 else "10.0.0.2",latency_ms=1)
    mon.collect(mp,test_fn=fake); state["n"]=1; mon.collect(mp,test_fn=fake)
    event="".join(p.read_text(encoding="utf-8-sig") for p in (TESTROOT/"monlogs").glob("*.csv"))
    record("Proxy đổi IP","EXIT_IP_CHANGED" in event,"monitor event emitted","SIMULATED")

    # Game crash: real dummy process mapping is removed.
    gdir=DATA/"phase3_test"/"A"; gst2=GameLauncher(TESTROOT/"crash_running.json")
    gst2.open_launcher("CRASH",str(gdir/"launcher.exe")); time.sleep(1); gst2.reconcile([{"name":"CRASH","game_path":str(gdir/"launcher.exe")}])
    pid=gst2._load().get("CRASH")
    if pid: subprocess.run(["taskkill","/PID",str(pid),"/T","/F"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    time.sleep(.5); clean=gst2.reconcile([{"name":"CRASH","game_path":str(gdir/"launcher.exe")}])
    record("Game crash",pid is not None and "CRASH" not in clean,f"pid={pid}")

    # Launcher crash/no game: no stale mapping is created.
    ldir=TESTROOT/"launcher_crash"; ldir.mkdir(exist_ok=True)
    shutil.copy2(DATA/"phase3_test"/"A"/"launcher.exe",ldir/"launcher.exe")
    glc=GameLauncher(TESTROOT/"launcher_crash.json")
    glc.open_launcher("LCRASH",str(ldir/"launcher.exe")); time.sleep(1)
    m=glc.reconcile([{"name":"LCRASH","game_path":str(ldir/"launcher.exe")}])
    record("Launcher crash","LCRASH" not in m,"launcher exited without game mapping")

    # Proxifier crash fail-closed path: simulated to avoid disrupting logged-in real clients.
    fl=FakeLauncher(); rg=RouteGuard(TESTROOT/"proxcrashlogs",retry_seconds=0)
    pp={"name":"X","proxy":"socks5://1.1.1.1:1","game_path":"x","fail_closed":True,"auto_reconnect":False}
    a=rg.observe(pp,{"status":"ROUTED"},False,fl)
    record("Proxifier crash",a.get("action")=="STOPPED" and "X" not in fl.running,f"action={a}","SIMULATED")

    # Reboot/stale state: simulate post-reboot stale running.json; cleanup must remove it.
    stale=TESTROOT/"reboot_running.json"; stale.write_text('{"OLD": 999999}',encoding="utf-8")
    gr=GameLauncher(stale); clean=gr.cleanup(valid_names=["OLD"])
    record("Stale PID sau reboot",clean=={} and gr._load()=={},"stale PID removed")
    record("Reboot Windows",clean=={},"post-reboot state recovery logic passed; no physical reboot performed","SIMULATED")

    # Updater must remain DIRECT: only game.exe/netprobe.exe are returned for routing.
    apps=[Path(x).name.lower() for x in _app_paths(REAL[0]["game_path"])]
    record("Update game","autoupdate.exe" not in apps and "upgameclient.exe" not in apps and "fsonline.exe" not in apps,f"routed apps={apps}")

    # Two profiles accidentally point to same executable: routing builder must reject.
    same=[{"name":"S1","proxy":"socks5://127.0.0.1:1","game_path":str(REAL[0]["game_path"])},{"name":"S2","proxy":"socks5://127.0.0.1:2","game_path":str(REAL[0]["game_path"])}]
    rejected=False
    try: build_profile(same,TESTROOT/"same.ppx")
    except ValueError: rejected=True
    record("Hai profile dùng nhầm cùng executable",rejected,"duplicate executable rejected")

    # Duplicate proxy warning logic.
    dup=MonitoringEngine(TESTROOT/"duplogs").duplicate_proxies([{"name":"A","proxy":"socks5://z:1"},{"name":"B","proxy":"socks5://z:1"}])
    record("Hai profile dùng trùng proxy",bool(dup),json.dumps(dup))

    # No DIRECT leak on fail-closed: dead-proxy netprobe already failed; guard also stops DIRECT.
    fl2=FakeLauncher(); rg2=RouteGuard(TESTROOT/"leaklogs",retry_seconds=0)
    pp2={"name":"X","proxy":"socks5://127.0.0.1:9","game_path":"x","fail_closed":True,"auto_reconnect":False}
    a2=rg2.observe(pp2,{"status":"DIRECT","detail":"leak"},True,fl2)
    record("Không leak DIRECT khi fail-closed",ec!=0 and a2.get("action")=="STOPPED" and "X" not in fl2.running,f"dead_proxy_exit={ec}, guard={a2}")

finally:
    for s in list(servers):
        try:s.stop()
        except:pass
    # Restore real production routing immediately.
    try:
        restore_apply(REAL)
        time.sleep(1)
    except Exception as e:
        print("RESTORE_ERROR",e)
    for p in TEMP_PPX:
        try:p.unlink()
        except:pass
    # persist report
    TESTROOT.mkdir(parents=True,exist_ok=True)
    (TESTROOT/"phase10_results.json").write_text(json.dumps(RESULTS,ensure_ascii=False,indent=2),encoding="utf-8")

print("SUMMARY",sum(1 for v in RESULTS.values() if v["ok"]),"/",len(RESULTS))
failed=[k for k,v in RESULTS.items() if not v["ok"]]
print("FAILED",failed)
if failed: raise SystemExit(2)
print("PHASE10_AUTOMATED_OK")
