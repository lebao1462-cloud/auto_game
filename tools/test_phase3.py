import os,sys,time,json
os.environ["QT_QPA_PLATFORM"]="offscreen"
sys.path.insert(0,r"D:\code\phongthan_proxy_manager")
from pathlib import Path
from game_launcher import GameLauncher
from profile_store import ProfileStore

base=Path(r"D:\code\phongthan_proxy_manager\data\phase3_test")
state=base/"running.json"
if state.exists(): state.unlink()
g=GameLauncher(state)
profiles=[
 {"name":"T-A","game_path":str(base/"A"/"launcher.exe"),"proxy":"","tag":"","note":""},
 {"name":"T-B","game_path":str(base/"B"/"launcher.exe"),"proxy":"","tag":"","note":""},
]

# Launch both real dummy clients and auto-detect by executable path
ra=g.open_launcher("T-A",profiles[0]["game_path"])
rb=g.open_launcher("T-B",profiles[1]["game_path"])
time.sleep(1.2)
m=g.reconcile(profiles)
assert set(m)=={"T-A","T-B"} and m["T-A"]!=m["T-B"],m
a1=m["T-A"]; b1=m["T-B"]
assert g.status("T-A",profiles[0]["game_path"])[0]
assert g.status("T-B",profiles[1]["game_path"])[0]

# stale cleanup and rename/delete mapping
raw=g._load(); raw["STALE"]=999999; g._save(raw)
clean=g.cleanup(valid_names=["T-A","T-B"])
assert "STALE" not in clean
g.rename_profile("T-A","T-A2")
assert "T-A2" in g._load() and "T-A" not in g._load()
g.rename_profile("T-A2","T-A")
g.remove_profile("T-B",stop=False)
assert "T-B" not in g._load()
m=g.reconcile(profiles)
assert "T-B" in m

# Restart selected equivalent: kill old A and spawn new A
g.restart("T-A",profiles[0]["game_path"])
time.sleep(1.2)
m=g.reconcile(profiles)
assert m["T-A"]!=a1 and g.alive(m["T-A"],g.expected_game_path(profiles[0]["game_path"]))

# Stop All
stopped=g.stop_all(profiles)
time.sleep(.5)
assert not g.reconcile(profiles)
print("CORE_OK",len(stopped))

# UI actions with the same dummy clients
import app as appmod
from PySide6.QtWidgets import QApplication
store=ProfileStore(base/"profiles_test.json")
store.save(profiles)
appmod.STORE=store
appmod.LAUNCHER=GameLauncher(base/"ui_running.json")
q=QApplication([])
w=appmod.App()
assert hasattr(w,"launch_all_btn") and hasattr(w,"stop_all_btn") and hasattr(w,"restart_btn") and hasattr(w,"restart_all_btn")
w.launch_all()
time.sleep(1.2)
w.refresh_runtime()
mapping=appmod.LAUNCHER.reconcile(store.load())
assert set(mapping)=={"T-A","T-B"},mapping
# crash one process externally, timer/reconcile must clean it
crash_pid=mapping["T-A"]
import subprocess
subprocess.run(["taskkill","/PID",str(crash_pid),"/T","/F"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
time.sleep(.5)
w.refresh_runtime()
assert "T-A" not in appmod.LAUNCHER._load()
# Stop remaining through UI
w.stop_all()
assert not appmod.LAUNCHER.reconcile(store.load())
print("UI_OK",w.profile_table.columnCount())
print("PHASE3_SMOKE_OK")
