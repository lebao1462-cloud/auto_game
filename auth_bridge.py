import select, socket, socketserver, struct, threading
from urllib.parse import urlparse, unquote
import socks

def _relay(a,b):
    try:
        while True:
            ready,_,_=select.select([a,b],[],[],1)
            if not ready: continue
            for src in ready:
                data=src.recv(65536)
                if not data: return
                (b if src is a else a).sendall(data)
    except Exception:
        pass

def _upstream(raw):
    u=urlparse(raw if "://" in raw else "socks5://"+raw)
    typ={"socks5":socks.SOCKS5,"socks4":socks.SOCKS4,"http":socks.HTTP,"https":socks.HTTP}.get(u.scheme.lower())
    if typ is None or not u.hostname or not u.port:
        raise ValueError("Authenticated upstream proxy không hợp lệ")
    return typ,u.hostname,int(u.port),unquote(u.username or ""),unquote(u.password or "")

class _BridgeServer(socketserver.ThreadingTCPServer):
    allow_reuse_address=True
    daemon_threads=True

class _Handler(socketserver.BaseRequestHandler):
    def handle(self):
        c=self.request
        h=c.recv(2)
        if len(h)<2 or h[0]!=5:return
        methods=c.recv(h[1])
        if 0 not in methods:
            c.sendall(b"\x05\xff"); return
        c.sendall(b"\x05\x00")
        h=c.recv(4)
        if len(h)<4 or h[0]!=5 or h[1]!=1:return
        atyp=h[3]
        if atyp==1: host=socket.inet_ntoa(c.recv(4))
        elif atyp==3:
            n=c.recv(1)
            if not n:return
            host=c.recv(n[0]).decode("idna")
        elif atyp==4: host=socket.inet_ntop(socket.AF_INET6,c.recv(16))
        else:return
        port=struct.unpack("!H",c.recv(2))[0]
        r=socks.socksocket()
        typ,phost,pport,user,password=self.server.upstream
        r.set_proxy(typ,phost,pport,username=user or None,password=password or None,rdns=True)
        try:
            r.settimeout(10); r.connect((host,port)); r.settimeout(None)
            c.sendall(b"\x05\x00\x00\x01"+socket.inet_aton("0.0.0.0")+b"\x00\x00")
            _relay(c,r)
        except Exception:
            try:c.sendall(b"\x05\x05\x00\x01"+socket.inet_aton("0.0.0.0")+b"\x00\x00")
            except:pass
        finally:
            try:r.close()
            except:pass

class AuthBridge:
    def __init__(self,raw):
        self.raw=raw
        self.server=_BridgeServer(("127.0.0.1",0),_Handler)
        self.server.upstream=_upstream(raw)
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
    @property
    def port(self): return int(self.server.server_address[1])
    def stop(self):
        try:self.server.shutdown()
        except:pass
        try:self.server.server_close()
        except:pass

class AuthBridgeManager:
    def __init__(self):
        self._bridges={}
        self._lock=threading.Lock()

    @staticmethod
    def key(raw):
        u=urlparse(raw if "://" in raw else "socks5://"+raw)
        return (u.scheme.lower(),u.hostname,int(u.port or 0),u.username or "",u.password or "")

    def ensure(self,raw):
        key=self.key(raw)
        with self._lock:
            b=self._bridges.get(key)
            if b is None:
                b=AuthBridge(raw); self._bridges[key]=b
            return b.port

    def retain(self,raw_values):
        keep={self.key(x) for x in raw_values}
        with self._lock:
            old=[k for k in self._bridges if k not in keep]
            bridges=[self._bridges.pop(k) for k in old]
        for b in bridges:b.stop()

    def local_port(self,raw):
        key=self.key(raw)
        with self._lock:
            b=self._bridges.get(key)
            return b.port if b else None
