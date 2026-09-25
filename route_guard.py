import csv, time
from datetime import datetime
from pathlib import Path
from proxy_core import test_proxy, masked_proxy

BAD_STATUSES={"DIRECT","PROXY DOWN"}

class RouteGuard:
    def __init__(self, log_dir, retry_seconds=10):
        self.log_dir=Path(log_dir); self.log_dir.mkdir(parents=True,exist_ok=True)
        self.retry_seconds=retry_seconds
        self.last_status={}
        self.stopped={}
        self._proxy_test=test_proxy

    def _log(self,name,event,status="",detail="",proxy=""):
        path=self.log_dir/f"route_events_{datetime.now():%Y-%m-%d}.csv"
        new=not path.exists()
        with open(path,"a",newline="",encoding="utf-8-sig") as f:
            w=csv.writer(f)
            if new: w.writerow(["Timestamp","Profile","Event","Status","Proxy","Detail"])
            w.writerow([datetime.now().isoformat(timespec="seconds"),name,event,status,masked_proxy(proxy),detail])

    def clear(self,name):
        self.stopped.pop(name,None)
        self.last_status.pop(name,None)

    def observe(self, profile, info, proxifier_ok, launcher):
        name=profile.get("name","")
        proxy=profile.get("proxy","").strip()
        path=profile.get("game_path","")
        status=info.get("status","OFFLINE")
        detail=info.get("detail","")
        running,pid=launcher.status(name,path)

        old=self.last_status.get(name)
        if old!=status:
            self._log(name,"ROUTE_STATUS",status,detail,proxy)
            self.last_status[name]=status

        fail_closed=bool(profile.get("fail_closed",True))
        auto_reconnect=bool(profile.get("auto_reconnect",True))
        reason=""
        if running and proxy and fail_closed:
            if not proxifier_ok:
                reason="Proxifier không chạy"
            elif status in BAD_STATUSES:
                reason=f"Routing {status}"

        if reason:
            launcher.stop(name)
            self.stopped[name]={"reason":reason,"at":time.time(),"last_retry":0.0,"relaunch_sent":False}
            self._log(name,"FAIL_CLOSED_STOP",status,reason,proxy)
            return {"action":"STOPPED","reason":reason}

        state=self.stopped.get(name)
        if state and running and status=="ROUTED":
            self._log(name,"RECOVERED","ROUTED","Game đã route lại qua proxy",proxy)
            self.stopped.pop(name,None)
            return {"action":"RECOVERED"}

        if state and not running and auto_reconnect and proxy and proxifier_ok and not state.get("relaunch_sent"):
            now=time.time()
            if now-state.get("last_retry",0)>=self.retry_seconds:
                state["last_retry"]=now
                result=self._proxy_test(proxy,timeout=4)
                if result.ok:
                    launcher.open_launcher(name,path)
                    state["relaunch_sent"]=True
                    self._log(name,"AUTO_RECONNECT","PROXY LIVE",f"Exit IP {result.ip}",proxy)
                    return {"action":"RELAUNCH","exit_ip":result.ip}
                self._log(name,"RECONNECT_WAIT","PROXY DOWN",result.error,proxy)
        return {"action":"NONE"}
