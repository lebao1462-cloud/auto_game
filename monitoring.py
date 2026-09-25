import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from proxy_core import test_proxy, masked_proxy

class MonitoringEngine:
    def __init__(self, log_dir):
        self.log_dir=Path(log_dir); self.log_dir.mkdir(parents=True,exist_ok=True)
        self.last={}
        self.last_duplicates=set()

    def collect(self, profiles, max_workers=8, test_fn=None):
        test_fn=test_fn or test_proxy
        proxies=[]
        seen=set()
        for p in profiles:
            raw=p.get("proxy","").strip()
            if raw and raw not in seen:
                seen.add(raw); proxies.append(raw)
        out={}
        if proxies:
            with ThreadPoolExecutor(max_workers=max(1,min(max_workers,len(proxies)))) as pool:
                futs={pool.submit(test_fn,p,4):p for p in proxies}
                for fut in as_completed(futs):
                    p=futs[fut]
                    try: r=fut.result()
                    except Exception as e:
                        from proxy_core import ProxyResult
                        r=ProxyResult(p,False,error=str(e)[:160])
                    out[p]={"ok":bool(r.ok),"ip":r.ip,"latency_ms":r.latency_ms,"error":r.error}
        self._events(profiles,out)
        self.last={k:dict(v) for k,v in out.items()}
        return out

    def duplicate_proxies(self, profiles):
        uses={}
        for p in profiles:
            raw=p.get("proxy","").strip()
            if raw: uses.setdefault(raw,[]).append(p.get("name",""))
        return {k:v for k,v in uses.items() if len(v)>1}

    def _write(self,event,profile="",proxy="",detail=""):
        path=self.log_dir/f"monitor_events_{datetime.now():%Y-%m-%d}.csv"
        new=not path.exists()
        with open(path,"a",newline="",encoding="utf-8-sig") as f:
            w=csv.writer(f)
            if new: w.writerow(["Timestamp","Event","Profile","Proxy","Detail"])
            w.writerow([datetime.now().isoformat(timespec="seconds"),event,profile,masked_proxy(proxy),detail])

    def _events(self,profiles,snapshot):
        by_proxy={}
        for p in profiles:
            raw=p.get("proxy","").strip()
            if raw: by_proxy.setdefault(raw,[]).append(p.get("name",""))
        for raw,cur in snapshot.items():
            prev=self.last.get(raw)
            names=",".join(by_proxy.get(raw,[]))
            if prev is None:
                self._write("PROXY_STATUS",names,raw,"LIVE" if cur["ok"] else f"DIE: {cur['error']}")
            elif bool(prev.get("ok"))!=bool(cur.get("ok")):
                self._write("PROXY_STATUS_CHANGE",names,raw,"LIVE" if cur["ok"] else f"DIE: {cur['error']}")
            if prev and prev.get("ok") and cur.get("ok") and prev.get("ip") and cur.get("ip") and prev.get("ip")!=cur.get("ip"):
                self._write("EXIT_IP_CHANGED",names,raw,f"{prev.get('ip')} -> {cur.get('ip')}")
        dups=self.duplicate_proxies(profiles)
        now=set(dups)
        for raw in now-self.last_duplicates:
            self._write("DUPLICATE_PROXY",",".join(dups[raw]),raw,"Nhiều profile dùng cùng proxy")
        self.last_duplicates=now
