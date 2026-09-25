import json, re, socket, subprocess, time, sys
from pathlib import Path
from urllib.parse import urlparse
from app_settings import AppSettings
from proxifier_router import route_proxy_target

CREATE_NO_WINDOW=0x08000000
BASE=Path(sys.executable).resolve().parent if getattr(sys,"frozen",False) else Path(__file__).resolve().parent
_CFG=AppSettings(BASE/"config.json",BASE).load()
LOG_FILE=Path(_CFG["log_dir"])/"proxifier"/"Log.txt"

_CACHE={"t":0.0,"data":[]}

def _proxy_target(raw):
    if not raw:
        return "",0,set()
    u=urlparse(raw if "://" in raw else "socks5://"+raw)
    host=u.hostname or ""; port=int(u.port or 0)
    ips=set()
    try:
        for x in socket.getaddrinfo(host,port,type=socket.SOCK_STREAM):
            ips.add(x[4][0])
    except Exception:
        if host: ips.add(host)
    return host,port,ips

def _connections():
    now=time.time()
    if now-_CACHE["t"]<0.7:
        return _CACHE["data"]
    cmd=r"""Get-NetTCPConnection -State Established -ErrorAction SilentlyContinue |
Select-Object OwningProcess,LocalAddress,LocalPort,RemoteAddress,RemotePort |
ConvertTo-Json -Compress"""
    r=subprocess.run(["powershell","-NoProfile","-Command",cmd],capture_output=True,text=True,creationflags=CREATE_NO_WINDOW)
    rows=[]
    if r.stdout.strip():
        try:
            data=json.loads(r.stdout)
            rows=data if isinstance(data,list) else [data]
        except Exception:
            rows=[]
    _CACHE.update(t=now,data=rows)
    return rows

def _proxifier_pids():
    cmd="Get-Process Proxifier -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id"
    r=subprocess.run(["powershell","-NoProfile","-Command",cmd],capture_output=True,text=True,creationflags=CREATE_NO_WINDOW)
    return {int(x) for x in r.stdout.split() if x.isdigit()}

def _latest_server_from_log(pid, proxy_raw=""):
    if not LOG_FILE.exists():
        return ""
    try:
        data=LOG_FILE.read_text(encoding="utf-8",errors="replace")
        lines=data.splitlines()[-5000:]
        rt=route_proxy_target(proxy_raw)
        phost=str(rt.get("connect_host","")); pport=int(rt.get("connect_port",0)); pips=set()
        try:
            for x in socket.getaddrinfo(phost,pport,type=socket.SOCK_STREAM): pips.add(x[4][0])
        except Exception:
            if phost: pips.add(phost)
        # Proxifier Normal log example:
        # game.exe - 116.118.95.93:7520 open through proxy 14.225.204.32:10800 SOCKS5
        pat=re.compile(r"game\.exe(?:\s*\(\d+\))?\s*-\s*([^\s]+):(\d+)\s+open through proxy\s+([^\s]+):(\d+)",re.I)
        for line in reversed(lines):
            m=pat.search(line)
            if not m: continue
            target_host=m.group(1).strip("[]")
            target_port=int(m.group(2))
            used_host=m.group(3).strip("[]")
            used_port=int(m.group(4))
            if proxy_raw:
                allowed={x.lower() for x in pips}; allowed.add(phost.lower())
                if used_port!=pport or used_host.lower() not in allowed:
                    continue
            if target_host not in ("127.0.0.1","::1"):
                return f"{target_host}:{target_port}"
    except Exception:
        pass
    return ""

def verify_profile(profile, launcher):
    name=profile.get("name","")
    proxy=profile.get("proxy","").strip()
    game_path=profile.get("game_path","").strip()
    running,pid=launcher.status(name,game_path)
    result={"status":"OFFLINE","pid":pid,"proxy_endpoint":"","game_server":"","detail":""}
    if not running:
        return result
    if not proxy:
        result.update(status="DIRECT",detail="Profile không cấu hình proxy")
        return result

    conns=_connections()
    game=[c for c in conns if int(c.get("OwningProcess") or 0)==int(pid)]
    direct=[c for c in game if str(c.get("RemoteAddress")) not in ("127.0.0.1","::1")]
    loop=[c for c in game if str(c.get("RemoteAddress")) in ("127.0.0.1","::1")]

    if direct:
        c=direct[0]
        result.update(status="DIRECT",game_server=f"{c.get('RemoteAddress')}:{c.get('RemotePort')}",detail="Phát hiện game kết nối trực tiếp")
        return result

    pxpids=_proxifier_pids()
    px=[c for c in conns if int(c.get("OwningProcess") or 0) in pxpids]
    rt=route_proxy_target(proxy)
    host=str(rt.get("connect_host","")); port=int(rt.get("connect_port",0)); ips=set()
    try:
        for x in socket.getaddrinfo(host,port,type=socket.SOCK_STREAM): ips.add(x[4][0])
    except Exception:
        if host: ips.add(host)
    match=[c for c in px if int(c.get("RemotePort") or 0)==port and str(c.get("RemoteAddress")) in ips]
    if match and loop:
        result["status"]="ROUTED"
        result["proxy_endpoint"]=f"{rt.get('display_host','')}:{rt.get('display_port',0)}"
        result["game_server"]=_latest_server_from_log(pid,proxy)
        result["detail"]="Game -> Proxifier -> auth bridge -> proxy" if rt.get("auth_bridge") else "Game -> Proxifier -> proxy"
        return result

    if loop:
        result.update(status="PROXY DOWN",detail=f"Game đã vào Proxifier nhưng chưa có kết nối tới {rt.get('display_host',host)}:{rt.get('display_port',port)}")
        return result
    if not game:
        result.update(status="ROUTING",detail="Game đang chạy nhưng chưa có TCP established để xác minh")
        return result
    result.update(status="ROUTING ERROR",detail="Có TCP nhưng không xác định được đường routing")
    return result

def verify_all(profiles, launcher):
    _CACHE["t"]=0.0
    _connections()
    return {p.get("name",""):verify_profile(p,launcher) for p in profiles}
