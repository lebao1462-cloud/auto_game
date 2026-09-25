import select, socket, socketserver, struct, sys, threading, time
from pathlib import Path
from urllib.parse import urlparse
import socks

ROOT=Path(r"D:\code\phongthan_proxy_manager")
sys.path.insert(0,str(ROOT))
from monitoring import MonitoringEngine

def relay(a,b):
    try:
        while True:
            r,_,_=select.select([a,b],[],[],1)
            if not r: continue
            for s in r:
                data=s.recv(65536)
                if not data:return
                (b if s is a else a).sendall(data)
    except Exception:
        pass

class S(socketserver.ThreadingTCPServer):
    allow_reuse_address=True
    daemon_threads=True

class H(socketserver.BaseRequestHandler):
    def handle(self):
        c=self.request
        h=c.recv(2)
        if len(h)<2 or h[0]!=5:return
        methods=c.recv(h[1])
        if 0 not in methods:
            c.sendall(b"\x05\xff"); return
        c.sendall(b"\x05\x00")
        h=c.recv(4)
        if len(h)<4 or h[1]!=1:return
        atyp=h[3]
        if atyp==1: host=socket.inet_ntoa(c.recv(4))
        elif atyp==3:
            n=c.recv(1)
            if not n:return
            host=c.recv(n[0]).decode()
        elif atyp==4: host=socket.inet_ntop(socket.AF_INET6,c.recv(16))
        else:return
        port=struct.unpack("!H",c.recv(2))[0]
        up=self.server.upstream
        try:
            if up:
                u=urlparse(up)
                r=socks.socksocket()
                r.set_proxy(socks.SOCKS5,u.hostname,u.port,rdns=True)
                r.settimeout(10); r.connect((host,port)); r.settimeout(None)
            else:
                r=socket.create_connection((host,port),timeout=10)
            c.sendall(b"\x05\x00\x00\x01"+socket.inet_aton("0.0.0.0")+b"\x00\x00")
            relay(c,r)
        except Exception:
            try:c.sendall(b"\x05\x05\x00\x01"+socket.inet_aton("0.0.0.0")+b"\x00\x00")
            except:pass
        finally:
            try:r.close()
            except:pass

logdir=ROOT/"data"/"phase10_ipchange_real"
logdir.mkdir(parents=True,exist_ok=True)
srv=S(("127.0.0.1",0),H); srv.upstream=None
t=threading.Thread(target=srv.serve_forever,daemon=True); t.start()
endpoint=f"socks5://127.0.0.1:{srv.server_address[1]}"
profiles=[{"name":"IPCHANGE","proxy":endpoint}]
m=MonitoringEngine(logdir)
try:
    first=m.collect(profiles)
    ip1=first[endpoint]["ip"]; ok1=first[endpoint]["ok"]
    print("FIRST",ok1,ip1)
    srv.upstream="socks5://160.187.0.89:1080"
    time.sleep(.5)
    second=m.collect(profiles)
    ip2=second[endpoint]["ip"]; ok2=second[endpoint]["ok"]
    print("SECOND",ok2,ip2)
    logs="".join(p.read_text(encoding="utf-8-sig") for p in logdir.glob("monitor_events_*.csv"))
    event="EXIT_IP_CHANGED" in logs
    print("EVENT",event)
    assert ok1 and ok2
    assert ip1 and ip2 and ip1!=ip2,(ip1,ip2)
    assert event
    print("PHYSICAL_EXIT_IP_CHANGE_OK")
finally:
    srv.shutdown(); srv.server_close()
