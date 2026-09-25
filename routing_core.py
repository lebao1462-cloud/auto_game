from pathlib import Path
import subprocess

PROXIFIER = Path(r"D:\code\phongthan_proxy_manager\tools\ProxifierPE\Proxifier PE\Proxifier.exe")

def parse_proxy(raw):
    from urllib.parse import urlparse
    u=urlparse(raw if "://" in raw else "socks5://"+raw)
    if not u.hostname or not u.port: raise ValueError("Proxy không hợp lệ")
    proto={"socks5":"SOCKS5","socks4":"SOCKS4","http":"HTTPS"}.get(u.scheme.lower())
    if not proto: raise ValueError("Chỉ hỗ trợ SOCKS4/SOCKS5/HTTP")
    return u,proto

def build_ppx(profiles,out_path):
    proxies=[]; rules=[]
    for p in profiles:
        raw=p.get("proxy","").strip()
        if not raw: continue
        u,proto=parse_proxy(raw); name="PX_"+p["name"]
        auth=""
        if u.username:
            auth=f'<Authentication enabled="true"><Username>{u.username}</Username><Password>{u.password or ""}</Password></Authentication>'
        proxies.append(f'<Proxy id="{len(proxies)+100}" type="{proto}"><Address>{u.hostname}</Address><Port>{u.port}</Port>{auth}</Proxy>')
        rules.append((p["name"],len(proxies)+99))
    proxy_xml="".join(proxies)
    rule_xml="".join(f'<Rule enabled="true"><Name>{n}</Name><Applications>game.exe</Applications><Action type="Proxy">{pid}</Action></Rule>' for n,pid in rules)
    xml=f'<?xml version="1.0" encoding="UTF-8"?><ProxifierProfile version="101" platform="Windows" product_id="0"><Options><Resolve><AutoModeDetection enabled="false"/></Resolve></Options><ProxyList>{proxy_xml}</ProxyList><ChainList/><RuleList>{rule_xml}<Rule enabled="true"><Name>Default</Name><Action type="Direct"/></Rule></RuleList></ProxifierProfile>'
    Path(out_path).write_text(xml,encoding="utf-8")
    return out_path

def open_profile(path):
    if not PROXIFIER.exists(): raise FileNotFoundError("Thiếu Proxifier Portable")
    subprocess.Popen([str(PROXIFIER),str(path)],cwd=str(PROXIFIER.parent))
