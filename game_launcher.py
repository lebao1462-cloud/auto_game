import json, subprocess, time
from pathlib import Path

CREATE_NO_WINDOW=0x08000000

class GameLauncher:
    def __init__(self,state_path):
        self.state_path=Path(state_path)
        self.state_path.parent.mkdir(parents=True,exist_ok=True)

    def _load(self):
        try:
            data=json.loads(self.state_path.read_text(encoding="utf-8-sig"))
            return data if isinstance(data,dict) else {}
        except Exception:
            return {}

    def _save(self,state):
        tmp=self.state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding="utf-8")
        tmp.replace(self.state_path)

    @staticmethod
    def _game_processes():
        cmd=r"""Get-CimInstance Win32_Process -Filter "name='game.exe'" |
Select-Object ProcessId,ExecutablePath | ConvertTo-Json -Compress"""
        r=subprocess.run(["powershell","-NoProfile","-Command",cmd],capture_output=True,text=True,creationflags=CREATE_NO_WINDOW)
        if r.returncode!=0 or not r.stdout.strip():
            return {}
        try:
            data=json.loads(r.stdout)
            rows=data if isinstance(data,list) else [data]
            out={}
            for x in rows:
                pid=x.get("ProcessId")
                if pid:
                    out[int(pid)]=str(x.get("ExecutablePath") or "")
            return out
        except Exception:
            return {}

    @classmethod
    def _game_pids(cls):
        return set(cls._game_processes())

    @staticmethod
    def expected_game_path(launcher_path):
        p=Path(launcher_path)
        return str((p.parent/"game.exe").resolve()).lower() if launcher_path else ""

    @classmethod
    def alive(cls,pid,expected_path=""):
        if not pid:
            return False
        procs=cls._game_processes()
        try: pid=int(pid)
        except Exception: return False
        if pid not in procs:
            return False
        if expected_path:
            actual=(procs.get(pid) or "").lower()
            return actual==str(Path(expected_path).resolve()).lower()
        return True

    def status(self,name,launcher_path=""):
        state=self._load(); pid=state.get(name)
        expected=self.expected_game_path(launcher_path) if launcher_path else ""
        ok=self.alive(pid,expected)
        if pid and not ok:
            state.pop(name,None); self._save(state)
        return ok, int(pid) if ok else None

    def adopt(self,name,pid,launcher_path=""):
        expected=self.expected_game_path(launcher_path) if launcher_path else ""
        if not self.alive(pid,expected):
            raise ValueError("PID không phải game.exe đúng của profile")
        state=self._load()
        for profile,oldpid in state.items():
            if profile!=name and int(oldpid)==int(pid):
                raise ValueError("PID đã gắn với profile khác")
        state[name]=int(pid); self._save(state); return int(pid)

    def reconcile(self,profiles):
        procs=self._game_processes()
        state=self._load()
        names={p.get("name","") for p in profiles}
        clean={}
        used=set()
        for p in profiles:
            name=p.get("name",""); launcher=p.get("game_path","")
            pid=state.get(name); expected=self.expected_game_path(launcher)
            if pid and int(pid) in procs and (not expected or (procs[int(pid)] or "").lower()==expected):
                clean[name]=int(pid); used.add(int(pid))
        for p in profiles:
            name=p.get("name",""); launcher=p.get("game_path","")
            if not name or name in clean or not launcher:
                continue
            expected=self.expected_game_path(launcher)
            matches=[pid for pid,path in procs.items() if pid not in used and (path or "").lower()==expected]
            if matches:
                pid=max(matches); clean[name]=pid; used.add(pid)
        if clean!=state:
            self._save(clean)
        return clean

    def open_launcher(self,name,launcher_path):
        p=Path(launcher_path)
        if not p.is_file():
            raise FileNotFoundError("Không tìm thấy launcher")
        running,pid=self.status(name,launcher_path)
        if running:
            return {"already_running":True,"pid":pid,"launcher_pid":None}
        proc=subprocess.Popen([str(p)],cwd=str(p.parent))
        return {"already_running":False,"pid":None,"launcher_pid":proc.pid}

    def launch(self,name,launcher_path,wait_seconds=45):
        result=self.open_launcher(name,launcher_path)
        if result["already_running"]:
            return result["pid"]
        end=time.time()+wait_seconds
        expected=self.expected_game_path(launcher_path)
        while time.time()<end:
            for pid,path in self._game_processes().items():
                if (path or "").lower()==expected:
                    return self.adopt(name,pid,launcher_path)
            time.sleep(1)
        raise TimeoutError("Launcher đã mở nhưng chưa phát hiện game.exe đúng profile")

    def stop(self,name):
        state=self._load(); pid=state.get(name)
        if pid and self.alive(pid):
            subprocess.run(["taskkill","/PID",str(pid),"/T","/F"],capture_output=True,creationflags=CREATE_NO_WINDOW)
        state.pop(name,None); self._save(state); return pid

    def stop_all(self,profiles=None):
        state=self._load()
        names=[p.get("name","") for p in profiles] if profiles is not None else list(state)
        stopped=[]
        for name in names:
            pid=self.stop(name)
            if pid: stopped.append((name,pid))
        return stopped

    def restart(self,name,launcher_path):
        self.stop(name)
        time.sleep(0.3)
        return self.open_launcher(name,launcher_path)

    def rename_profile(self,old_name,new_name):
        if old_name==new_name: return
        state=self._load()
        if old_name in state:
            state[new_name]=state.pop(old_name); self._save(state)

    def remove_profile(self,name,stop=False):
        if stop: self.stop(name); return
        state=self._load()
        if name in state:
            state.pop(name,None); self._save(state)

    def cleanup(self,valid_names=None):
        state=self._load()
        names=set(valid_names) if valid_names is not None else None
        clean={}
        for k,v in state.items():
            if names is not None and k not in names: continue
            if self.alive(v): clean[k]=int(v)
        if clean!=state: self._save(clean)
        return clean
