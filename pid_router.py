from dataclasses import dataclass
from pathlib import Path
import json, subprocess

WINDIVERT_DIR = Path(r"D:\code\phongthan_proxy_manager\tools\WinDivert\WinDivert-2.2.2-A\x64")
STATE = Path(r"D:\code\phongthan_proxy_manager\data\routing.json")

@dataclass
class RouteState:
    profile: str
    game_pid: int
    proxy: str
    status: str = "READY"

class PidRouter:
    def __init__(self, state_path=STATE):
        self.state_path=Path(state_path)
        self.state_path.parent.mkdir(parents=True,exist_ok=True)

    def prerequisites(self):
        required=["WinDivert.dll","WinDivert64.sys"]
        missing=[x for x in required if not (WINDIVERT_DIR/x).exists()]
        return not missing, missing

    def save(self, rows):
        self.state_path.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")

    def load(self):
        try: return json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception: return {}

    @staticmethod
    def process_alive(pid):
        r=subprocess.run(["powershell","-NoProfile","-Command",f"Get-Process -Id {int(pid)} -ErrorAction SilentlyContinue | Select -Expand Id"],capture_output=True,text=True,creationflags=0x08000000)
        return str(pid) in r.stdout.split()

    def bind(self, profile, pid, proxy):
        if not self.process_alive(pid): raise ValueError("game.exe không còn chạy")
        if not proxy.strip(): raise ValueError("Profile chưa được gán proxy")
        state=self.load()
        state[profile]={"pid":int(pid),"proxy":proxy.strip(),"status":"READY"}
        self.save(state)
        return state[profile]

    def unbind(self, profile):
        state=self.load(); state.pop(profile,None); self.save(state)
