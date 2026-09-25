import subprocess, time, ctypes, winreg, sys
from ctypes import wintypes
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape
from app_settings import AppSettings
from safe_io import atomic_write_text, atomic_write_json
from auth_bridge import AuthBridgeManager

BASE=Path(sys.executable).resolve().parent if getattr(sys,"frozen",False) else Path(__file__).resolve().parent
_CFG=AppSettings(BASE/"config.json",BASE).load()
PROXIFIER=Path(_CFG["tool_dir"])/"ProxifierStandard"/"Proxifier.exe"
PROFILE=Path(_CFG["data_dir"])/"routing_active.ppx"
APPLY_PROFILE=Path(_CFG["data_dir"])/"routing_apply.ppx"
STATE=Path(_CFG["data_dir"])/"routing_state.json"
CREATE_NO_WINDOW=0x08000000
LOG_DIR=Path(_CFG["log_dir"])/"proxifier"
SETUP=Path(_CFG["tool_dir"])/"ProxifierSetup.exe"
_BRIDGES=AuthBridgeManager()
_AUTH_ROUTE_MAP={}

def _parse(raw):
    u=urlparse(raw if "://" in raw else "socks5://"+raw)
    if not u.hostname or not u.port:
        raise ValueError("Proxy không hợp lệ")
    typ={"socks5":"SOCKS5","socks4":"SOCKS4","http":"HTTPS","https":"HTTPS"}.get(u.scheme.lower())
    if not typ:
        raise ValueError("Chỉ hỗ trợ SOCKS4/SOCKS5/HTTP(S)")
    return u,typ

def _prepare_profiles(profiles):
    global _AUTH_ROUTE_MAP
    effective=[]; auth_values=[]; route_map={}
    for p in profiles:
        q=dict(p)
        raw=str(q.get("proxy","") or "").strip()
        if raw:
            u,_=_parse(raw)
            if u.username is not None:
                port=_BRIDGES.ensure(raw)
                q["proxy"]=f"socks5://127.0.0.1:{port}"
                auth_values.append(raw)
                route_map[raw]=port
        effective.append(q)
    _BRIDGES.retain(auth_values)
    _AUTH_ROUTE_MAP=route_map
    return effective,bool(auth_values)

def route_proxy_target(raw):
    raw=(raw or "").strip()
    if not raw:
        return {"connect_host":"","connect_port":0,"display_host":"","display_port":0,"auth_bridge":False}
    u,_=_parse(raw)
    if raw in _AUTH_ROUTE_MAP:
        return {
            "connect_host":"127.0.0.1",
            "connect_port":int(_AUTH_ROUTE_MAP[raw]),
            "display_host":u.hostname or "",
            "display_port":int(u.port or 0),
            "auth_bridge":True,
        }
    return {
        "connect_host":u.hostname or "",
        "connect_port":int(u.port or 0),
        "display_host":u.hostname or "",
        "display_port":int(u.port or 0),
        "auth_bridge":False,
    }

def _app_paths(launcher):
    d=Path(launcher).parent
    names=["game.exe","netprobe.exe"]
    return [str(d/n) for n in names if (d/n).exists()]

def build_profile(profiles, out=PROFILE):
    proxies=[]; rules=[]; proxy_id=100; seen_apps={}
    for p in profiles:
        raw=p.get("proxy","").strip()
        launcher=p.get("game_path","").strip()
        if not raw or not launcher:
            continue
        u,typ=_parse(raw)
        if u.username is not None:
            raise ValueError("Authenticated proxy phải đi qua apply() để dùng auth bridge an toàn")
        proxies.append(f"<Proxy id=\"{proxy_id}\" type=\"{typ}\"><Address>{escape(u.hostname)}</Address><Port>{u.port}</Port><Options>48</Options></Proxy>")
        app_list=_app_paths(launcher)
        if not app_list:
            raise FileNotFoundError(f"Không tìm thấy client cho {p.get('name','profile')}")
        for app in app_list:
            key=str(Path(app).resolve()).lower()
            if key in seen_apps:
                raise ValueError(f"Executable bị dùng bởi nhiều profile: {app} ({seen_apps[key]} và {p.get('name','profile')})")
            seen_apps[key]=p.get("name","profile")
        apps="; ".join(app_list)
        rules.append(f"<Rule enabled=\"true\"><Name>{escape(p.get('name','Profile'))}</Name><Applications>{escape(apps)}</Applications><Action type=\"Proxy\">{proxy_id}</Action></Rule>")
        proxy_id+=1
    if not rules:
        raise ValueError("Chưa có profile đủ Proxy + Game path")
    xml='<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    xml+='<ProxifierProfile version="102" platform="Windows" product_id="0" product_minver="400">'
    xml+='<Options><Resolve><AutoModeDetection enabled="true"/><ViaProxy enabled="false"><TryLocalDnsFirst enabled="false"/></ViaProxy><ExclusionList>%ComputerName%; localhost; *.local</ExclusionList><DnsUdpMode>0</DnsUdpMode></Resolve><Encryption mode="basic"/><HttpProxiesSupport enabled="false"/><HandleDirectConnections enabled="false"/><ConnectionLoopDetection enabled="true"/><ProcessServices enabled="false"/><ProcessOtherUsers enabled="false"/></Options>'
    xml+='<ProxyList>'+''.join(proxies)+'</ProxyList><ChainList/><RuleList>'
    xml+='<Rule enabled="true"><Name>Localhost</Name><Targets>localhost; 127.0.0.1; ::1; %ComputerName%</Targets><Action type="Direct"/></Rule>'
    xml+=''.join(rules)
    xml+='<Rule enabled="true"><Name>Default</Name><Action type="Direct"/></Rule></RuleList></ProxifierProfile>'
    out=Path(out); out.parent.mkdir(parents=True,exist_ok=True); atomic_write_text(out,xml,encoding="utf-8",backup=True,backup_dir=out.parent/"backups")
    return out

def driver_ready():
    r=subprocess.run(["powershell","-NoProfile","-Command","$s=Get-Service ProxifierDrv -ErrorAction SilentlyContinue; if($s){$s.Status}"],capture_output=True,text=True,creationflags=CREATE_NO_WINDOW)
    return (r.stdout or "").strip().lower()=="running"

def install_proxifier_elevated():
    if not SETUP.exists():
        raise FileNotFoundError(f"Không tìm thấy Proxifier installer: {SETUP}")
    target=Path(_CFG["tool_dir"])/"ProxifierStandard"
    params=f'/VERYSILENT /SUPPRESSMSGBOXES /NORESTART /DIR="{target}"'
    rc=ctypes.windll.shell32.ShellExecuteW(None,"runas",str(SETUP),params,str(SETUP.parent),1)
    return int(rc)>32

def _proxifier_running():
    r=subprocess.run(["powershell","-NoProfile","-Command","(Get-Process Proxifier -ErrorAction SilentlyContinue).Count"],capture_output=True,text=True,creationflags=CREATE_NO_WINDOW)
    try: return int((r.stdout or "0").strip())>0
    except: return False

def _dismiss_trial():
    user32=ctypes.windll.user32
    EnumProc=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
    @EnumProc
    def cb(hwnd,lparam):
        title=ctypes.create_unicode_buffer(256); user32.GetWindowTextW(hwnd,title,256)
        if title.value=="Proxifier Trial":
            child=user32.GetDlgItem(hwnd,1)
            if child: user32.PostMessageW(child,0x00F5,0,0)
        return True
    user32.EnumWindows(cb,0)

def enable_file_logging():
    LOG_DIR.mkdir(parents=True,exist_ok=True)
    key=winreg.CreateKey(winreg.HKEY_CURRENT_USER,r"Software\Initex\Proxifier\Settings")
    winreg.SetValueEx(key,"LogPath",0,winreg.REG_SZ,str(LOG_DIR))
    winreg.SetValueEx(key,"LogLevelFile",0,winreg.REG_DWORD,2)
    winreg.CloseKey(key)
    return str(LOG_DIR)

def apply(profiles):
    if not PROXIFIER.exists():
        raise FileNotFoundError("Chưa cài Proxifier Standard")
    enable_file_logging()
    effective,has_auth=_prepare_profiles(profiles)
    # Authenticated upstreams are converted to local no-auth SOCKS bridges.
    # Credentials stay in memory/DPAPI and never enter a Proxifier profile.
    ppx=build_profile(effective,APPLY_PROFILE)
    if not _proxifier_running():
        subprocess.Popen([str(PROXIFIER)],cwd=str(PROXIFIER.parent))
        time.sleep(2); _dismiss_trial(); time.sleep(1)
    else:
        _dismiss_trial()
    subprocess.Popen([str(PROXIFIER),str(ppx),"silent-load"],cwd=str(PROXIFIER.parent))
    time.sleep(1)
    atomic_write_json(STATE,{
        "active":True,
        "profiles":[p.get("name","") for p in profiles if p.get("proxy","").strip() and p.get("game_path","").strip()],
        "authenticated_proxy":bool(has_auth),
        "updated_at":time.strftime("%Y-%m-%dT%H:%M:%S"),
    },backup=True,backup_dir=STATE.parent/"backups")
    if has_auth:
        try: Path(ppx).unlink()
        except Exception: pass
    else:
        # Non-auth profile is safe to keep as the active routing snapshot.
        if Path(ppx)!=PROFILE:
            atomic_write_text(PROFILE,Path(ppx).read_text(encoding="utf-8"),backup=True,backup_dir=PROFILE.parent/"backups")
            try: Path(ppx).unlink()
            except Exception: pass
    return str(STATE)

def active():
    return _proxifier_running() and STATE.exists()
