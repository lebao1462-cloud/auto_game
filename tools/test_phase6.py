import sys,tempfile
sys.path.insert(0,r"D:\code\phongthan_proxy_manager")
from pathlib import Path
from monitoring import MonitoringEngine
from proxy_core import ProxyResult

root=Path(tempfile.mkdtemp(prefix="pt_phase6_",dir=r"D:\code\phongthan_proxy_manager\data"))
engine=MonitoringEngine(root)
profiles=[
 {"name":"A","proxy":"socks5://x:1"},
 {"name":"B","proxy":"socks5://x:1"},
 {"name":"C","proxy":"socks5://y:2"},
]
state={"round":0}
def fake(raw,timeout=4):
    r=state["round"]
    if raw.endswith("x:1"):
        if r==0:return ProxyResult(raw,True,"10.0.0.1",11)
        if r==1:return ProxyResult(raw,True,"10.0.0.2",12)
        return ProxyResult(raw,False,error="dead")
    return ProxyResult(raw,True,"20.0.0.1",22)

s1=engine.collect(profiles,test_fn=fake)
assert s1["socks5://x:1"]["ok"] and engine.duplicate_proxies(profiles)
state["round"]=1
s2=engine.collect(profiles,test_fn=fake)
assert s2["socks5://x:1"]["ip"]=="10.0.0.2"
state["round"]=2
s3=engine.collect(profiles,test_fn=fake)
assert not s3["socks5://x:1"]["ok"]
logs=list(root.glob("monitor_events_*.csv"))
data=logs[0].read_text(encoding="utf-8-sig")
for token in ("DUPLICATE_PROXY","EXIT_IP_CHANGED","PROXY_STATUS_CHANGE"):
    assert token in data,token
print("PHASE6_EVENTS_OK")
