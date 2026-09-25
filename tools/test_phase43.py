import os,sys,time,tempfile
os.environ["QT_QPA_PLATFORM"]="offscreen"
sys.path.insert(0,r"D:\code\phongthan_proxy_manager")
from pathlib import Path
import routing_verify as rv

root=Path(tempfile.mkdtemp(prefix="pt_phase43_",dir=r"D:\code\phongthan_proxy_manager\data"))
log=root/"Log.txt"
log.write_text(
"[2026.09.25 16:20:00] game.exe - 116.118.95.93:7520 open through proxy 14.225.204.32:10800 SOCKS5\n"
"[2026.09.25 16:20:01] game.exe - 116.118.95.93:7296 open through proxy 160.187.0.89:1080 SOCKS5\n",
encoding="utf-8")
rv.LOG_FILE=log
assert rv._latest_server_from_log(1,"socks5://14.225.204.32:10800")=="116.118.95.93:7520"
assert rv._latest_server_from_log(2,"socks5://160.187.0.89:1080")=="116.118.95.93:7296"
print("LOG_PARSER_OK")

# Safe proxy-change workflow with dummy Phase3 client
import app as appmod
from profile_store import ProfileStore
from game_launcher import GameLauncher
from PySide6.QtWidgets import QApplication

base=Path(r"D:\code\phongthan_proxy_manager\data\phase3_test")
store=ProfileStore(root/"profiles.json")
store.save([{"name":"SAFE","proxy":"socks5://1.1.1.1:1080","game_path":str(base/"A"/"launcher.exe"),"tag":"","note":""}])
launcher=GameLauncher(root/"running.json")
launcher.open_launcher("SAFE",str(base/"A"/"launcher.exe"))
time.sleep(1)
launcher.reconcile(store.load())
oldpid=launcher._load()["SAFE"]
appmod.STORE=store; appmod.LAUNCHER=launcher; appmod.apply_routing=lambda profiles: str(root/"dummy.ppx")
q=QApplication([])
w=appmod.App()
w.profile_table.selectRow(0)
w.begin_edit()
w.proxy_combo.setCurrentText("socks5://2.2.2.2:1080")
w.save_profile()
time.sleep(1)
launcher.reconcile(store.load())
newpid=launcher._load()["SAFE"]
assert newpid!=oldpid,(oldpid,newpid)
assert store.load()[0]["proxy"]=="socks5://2.2.2.2:1080"
launcher.stop_all(store.load())
print("SAFE_PROXY_CHANGE_OK",oldpid,newpid)
print("PHASE43_SMOKE_OK")
