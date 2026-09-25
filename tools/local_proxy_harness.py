import base64, select, socket, socketserver, struct, threading

def tunnel(a,b):
    try:
        while True:
            r,_,_=select.select([a,b],[],[],1)
            if not r: continue
            for s in r:
                data=s.recv(65536)
                if not data: return
                (b if s is a else a).sendall(data)
    except Exception:
        pass

class _Server(socketserver.ThreadingTCPServer):
    allow_reuse_address=True
    daemon_threads=True
    def __init__(self,*a,**k):
        super().__init__(*a,**k); self.clients=set(); self.clients_lock=threading.Lock()
    def track(self,s):
        with self.clients_lock:self.clients.add(s)
    def untrack(self,s):
        with self.clients_lock:self.clients.discard(s)
    def close_clients(self):
        with self.clients_lock: items=list(self.clients)
        for s in items:
            try:s.shutdown(socket.SHUT_RDWR)
            except:pass
            try:s.close()
            except:pass

class SocksHandler(socketserver.BaseRequestHandler):
    def handle(self):
        c=self.request; self.server.track(c); auth=self.server.auth
        h=c.recv(2)
        if len(h)<2:return
        ver,n=h; methods=c.recv(n)
        method=2 if auth else 0
        if method not in methods:
            c.sendall(b"\x05\xff"); return
        c.sendall(bytes([5,method]))
        if method==2:
            v=c.recv(2)
            if len(v)<2:return
            _,ul=v; user=c.recv(ul).decode(errors="ignore")
            pl=c.recv(1)
            if not pl:return
            password=c.recv(pl[0]).decode(errors="ignore")
            ok=(user,password)==auth
            c.sendall(bytes([1,0 if ok else 1]))
            if not ok:return
        h=c.recv(4)
        if len(h)<4:return
        ver,cmd,_,atyp=h
        if cmd!=1:return
        if atyp==1: host=socket.inet_ntoa(c.recv(4))
        elif atyp==3:
            ln=c.recv(1)[0]; host=c.recv(ln).decode()
        elif atyp==4: host=socket.inet_ntop(socket.AF_INET6,c.recv(16))
        else:return
        port=struct.unpack("!H",c.recv(2))[0]
        try:
            r=socket.create_connection((host,port),timeout=8)
            bind=r.getsockname()
            c.sendall(b"\x05\x00\x00\x01"+socket.inet_aton("0.0.0.0")+struct.pack("!H",0))
            tunnel(c,r)
        except Exception:
            try:c.sendall(b"\x05\x05\x00\x01"+socket.inet_aton("0.0.0.0")+b"\x00\x00")
            except:pass

class HttpHandler(socketserver.BaseRequestHandler):
    def handle(self):
        c=self.request; self.server.track(c); data=b""
        while b"\r\n\r\n" not in data and len(data)<65536:
            x=c.recv(4096)
            if not x:return
            data+=x
        lines=data.decode("iso-8859-1",errors="ignore").split("\r\n")
        first=lines[0].split()
        if len(first)<2 or first[0].upper()!="CONNECT":
            c.sendall(b"HTTP/1.1 405 Method Not Allowed\r\n\r\n"); return
        if self.server.auth:
            expected="Basic "+base64.b64encode(f"{self.server.auth[0]}:{self.server.auth[1]}".encode()).decode()
            headers={k.strip().lower():v.strip() for line in lines[1:] if ":" in line for k,v in [line.split(":",1)]}
            if headers.get("proxy-authorization")!=expected:
                c.sendall(b"HTTP/1.1 407 Proxy Authentication Required\r\nProxy-Authenticate: Basic realm=test\r\n\r\n"); return
        hp=first[1]
        host,port=hp.rsplit(":",1)
        host=host.strip("[]")
        try:
            r=socket.create_connection((host,int(port)),timeout=8)
            c.sendall(b"HTTP/1.1 200 Connection Established\r\n\r\n")
            tunnel(c,r)
        except Exception:
            try:c.sendall(b"HTTP/1.1 502 Bad Gateway\r\n\r\n")
            except:pass

class ProxyServer:
    def __init__(self,kind="socks",auth=None,port=0):
        handler=SocksHandler if kind=="socks" else HttpHandler
        self.server=_Server(("127.0.0.1",port),handler); self.server.auth=auth
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
    @property
    def port(self): return self.server.server_address[1]
    def start(self): self.thread.start(); return self
    def stop(self):
        self.server.close_clients(); self.server.shutdown(); self.server.server_close()
