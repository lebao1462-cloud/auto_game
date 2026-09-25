import sys,shutil,subprocess,time,json
from pathlib import Path
ROOT=Path(r"D:\code\phongthan_proxy_manager")
sys.path.insert(0,str(ROOT)); sys.path.insert(0,str(ROOT/"tools"))
from local_proxy_harness import ProxyServer
from profile_store import ProfileStore
from proxifier_router import apply, route_proxy_target, APPLY_PROFILE
from routing_verify import LOG_FILE
real=ProfileStore(ROOT/"data"/"profiles.json").load()
d=ROOT/"data"/"auth_bridge_test"; d.mkdir(exist_ok=True)
shutil.copy2(Path(r"D:\PhongThanProfiles\ACC-01\netprobe.exe"),d/"netprobe.exe")
shutil.copy2(Path(r"D:\PhongThanProfiles\ACC-01\netprobe.exe"),d/"launcher.exe")
s=ProxyServer("socks",auth=("user","Pass123!")).start()
try:
    p={"name":"AUTH-BRIDGE","proxy":f"socks5://user:Pass123!@127.0.0.1:{s.port}","game_path":str(d/"launcher.exe")}
    apply(real+[p]); time.sleep(1)
    rt=route_proxy_target(p["proxy"]); print("ROUTE_TARGET",rt)
    r=subprocess.run([str(d/"netprobe.exe")],capture_output=True,text=True,timeout=20)
    print("NETPROBE",r.returncode,(r.stdout+r.stderr).strip())
    txt=LOG_FILE.read_text(encoding="utf-8",errors="replace")[-20000:] if LOG_FILE.exists() else ""
    local=f"127.0.0.1:{rt['connect_port']}"
    print("LOG_BRIDGE",local in txt)
    print("APPLY_PROFILE_EXISTS",APPLY_PROFILE.exists())
    assert r.returncode==0
    assert local in txt and "open through proxy" in txt
    assert "Pass123!" not in txt
    assert not APPLY_PROFILE.exists()
    print("AUTH_BRIDGE_PRODUCTION_OK")
finally:
    s.stop()
    apply(real)
