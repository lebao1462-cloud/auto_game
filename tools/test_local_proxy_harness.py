import sys,time
sys.path.insert(0,r"D:\code\phongthan_proxy_manager")
sys.path.insert(0,r"D:\code\phongthan_proxy_manager\tools")
from local_proxy_harness import ProxyServer
from proxy_core import test_proxy

servers=[]
try:
    s=ProxyServer("socks").start(); servers.append(s)
    r=test_proxy(f"socks5://127.0.0.1:{s.port}",timeout=10); print("SOCKS",r); assert r.ok
    a=ProxyServer("socks",auth=("u","p")).start(); servers.append(a)
    r=test_proxy(f"socks5://u:p@127.0.0.1:{a.port}",timeout=10); print("SOCKS_AUTH",r); assert r.ok
    h=ProxyServer("http").start(); servers.append(h)
    r=test_proxy(f"http://127.0.0.1:{h.port}",timeout=10); print("HTTP",r); assert r.ok
    ha=ProxyServer("http",auth=("u","p")).start(); servers.append(ha)
    r=test_proxy(f"http://u:p@127.0.0.1:{ha.port}",timeout=10); print("HTTP_AUTH",r); assert r.ok
    print("LOCAL_PROXY_HARNESS_OK")
finally:
    for x in servers:x.stop()
