import json, shutil, subprocess, sys, time
from pathlib import Path

ROOT=Path(r"D:\code\phongthan_proxy_manager")
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/"tools"))

from local_proxy_harness import ProxyServer
from profile_store import ProfileStore
from game_launcher import GameLauncher
from proxifier_router import apply, active
from routing_verify import verify_profile
from route_guard import RouteGuard

real=ProfileStore(ROOT/"data"/"profiles.json").load()
testdir=ROOT/"data"/"phase10_proxifier_crash_real"
testdir.mkdir(parents=True,exist_ok=True)
# use dummy game that keeps opening TCP
src=ROOT/"data"/"phase10"/"deadplay"
shutil.copy2(src/"game.exe",testdir/"game.exe")
shutil.copy2(src/"launcher.exe",testdir/"launcher.exe")

srv=ProxyServer("socks").start()
profile={
    "name":"P10-PROX-CRASH",
    "proxy":f"socks5://127.0.0.1:{srv.port}",
    "game_path":str(testdir/"launcher.exe"),
    "fail_closed":True,
    "auto_reconnect":False,
}
launcher=GameLauncher(testdir/"running.json")
guard=RouteGuard(testdir/"logs",retry_seconds=0)
try:
    apply(real+[profile]); time.sleep(1)
    launcher.open_launcher(profile["name"],profile["game_path"])
    time.sleep(2)
    launcher.reconcile([profile])
    before=verify_profile(profile,launcher)
    print("BEFORE",json.dumps(before,ensure_ascii=False))
    running,pid=launcher.status(profile["name"],profile["game_path"])
    assert running and pid
    assert before.get("status") in ("ROUTED","ROUTING"),before

    subprocess.run(["taskkill","/IM","Proxifier.exe","/F"],capture_output=True,text=True)
    time.sleep(1)
    print("PROXIFIER_ACTIVE_AFTER_KILL",active())
    assert not active()

    action=guard.observe(profile,before,active(),launcher)
    time.sleep(.5)
    alive,_=launcher.status(profile["name"],profile["game_path"])
    print("GUARD_ACTION",action,"DUMMY_ALIVE",alive)
    assert action.get("action")=="STOPPED"
    assert not alive
    print("PHYSICAL_PROXIFIER_CRASH_FAILCLOSED_OK")
finally:
    try: launcher.stop(profile["name"])
    except: pass
    try: srv.stop()
    except: pass
    apply(real)
    time.sleep(2)
