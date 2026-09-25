from dataclasses import dataclass
from urllib.parse import quote
import time, requests

@dataclass
class ProxyResult:
    proxy: str
    ok: bool
    ip: str = ""
    latency_ms: int = 0
    error: str = ""

def normalize_proxy(raw: str) -> str:
    raw = raw.strip()
    if not raw:
        raise ValueError("Proxy trống")
    if "://" in raw:
        return raw
    parts = raw.split(":")
    if len(parts) == 2:
        host, port = parts
        return f"http://{host}:{port}"
    if len(parts) == 4:
        host, port, user, password = parts
        return f"http://{quote(user, safe='')}:{quote(password, safe='')}@{host}:{port}"
    raise ValueError("Dùng IP:PORT, IP:PORT:USER:PASS hoặc URL http/socks5")

def masked_proxy(raw: str) -> str:
    parts = raw.strip().split(":")
    if "://" not in raw and len(parts) == 4:
        return f"{parts[0]}:{parts[1]}:{parts[2]}:********"
    if "@" in raw and "://" in raw:
        scheme, rest = raw.split("://", 1)
        auth, host = rest.rsplit("@", 1)
        user = auth.split(":", 1)[0]
        return f"{scheme}://{user}:********@{host}"
    return raw.strip()

def test_proxy(raw: str, timeout=8) -> ProxyResult:
    try:
        url = normalize_proxy(raw)
        started = time.perf_counter()
        r = requests.get("https://api.ipify.org?format=json",
                         proxies={"http": url, "https": url},
                         timeout=timeout)
        r.raise_for_status()
        latency = int((time.perf_counter() - started) * 1000)
        return ProxyResult(raw, True, r.json().get("ip", ""), latency)
    except Exception as exc:
        return ProxyResult(raw, False, error=str(exc)[:160])
