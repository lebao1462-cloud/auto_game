import os,sys,tempfile
sys.path.insert(0,r"D:\code\phongthan_proxy_manager")
from pathlib import Path
from route_guard import RouteGuard
from proxy_core import ProxyResult

class FakeLauncher:
    def __init__(self): self.running={"A":111}; self.opened=[]; self.stopped=[]
    def status(self,name,path=""): return (name in self.running,self.running.get(name))
    def stop(self,name): self.stopped.append(name); return self.running.pop(name,None)
    def open_launcher(self,name,path): self.opened.append((name,path)); self.running[name]=222; return {"already_running":False,"pid":None,"launcher_pid":999}

root=Path(tempfile.mkdtemp(prefix="pt_phase5_",dir=r"D:\code\phongthan_proxy_manager\data"))
g=RouteGuard(root,retry_seconds=0)
f=FakeLauncher()
p={"name":"A","proxy":"socks5://1.2.3.4:1080","game_path":r"D:\x\launcher.exe","fail_closed":True,"auto_reconnect":True}

# DIRECT => stop
r=g.observe(p,{"status":"DIRECT","detail":"leak"},True,f)
assert r["action"]=="STOPPED" and "A" not in f.running

# dead proxy => no relaunch
g._proxy_test=lambda *a,**k: ProxyResult(a[0],False,error="dead")
r=g.observe(p,{"status":"OFFLINE"},True,f)
assert r["action"]=="NONE" and not f.opened

# proxy alive => relaunch
g._proxy_test=lambda *a,**k: ProxyResult(a[0],True,ip="8.8.8.8",latency_ms=1)
r=g.observe(p,{"status":"OFFLINE"},True,f)
assert r["action"]=="RELAUNCH" and f.opened

# routed => recovery clears guard state
r=g.observe(p,{"status":"ROUTED","detail":"ok"},True,f)
assert r["action"]=="RECOVERED" and "A" not in g.stopped

# fail_closed false does not stop DIRECT
p2=dict(p); p2["fail_closed"]=False; f.running["A"]=333
r=g.observe(p2,{"status":"DIRECT"},True,f)
assert r["action"]=="NONE" and "A" in f.running

logs=list(root.glob("route_events_*.csv"))
assert logs and "FAIL_CLOSED_STOP" in logs[0].read_text(encoding="utf-8-sig")
print("PHASE5_GUARD_OK")
print("LOG_OK",logs[0].name)
