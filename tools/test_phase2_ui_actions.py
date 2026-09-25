import os,sys,tempfile,json
os.environ["QT_QPA_PLATFORM"]="offscreen"
sys.path.insert(0,r"D:\code\phongthan_proxy_manager")
from pathlib import Path
from PySide6.QtWidgets import QApplication,QFileDialog
import app as appmod
from profile_store import ProfileStore

root=Path(tempfile.mkdtemp(prefix="pt_phase2_ui_",dir=r"D:\code\phongthan_proxy_manager\data"))
store=ProfileStore(root/"profiles.json")
store.add("UI-A","socks5://1.1.1.1:1080",r"D:\A\autoupdate.exe","TagA","NoteA")
appmod.STORE=store
q=QApplication([])
w=appmod.App()

# clone actual UI method
w.profile_table.selectRow(0)
w.clone_profile()
assert len(store.load())==2 and store.load()[1]["name"].startswith("UI-A Copy")

# export actual UI method
export_path=str(root/"ui_export.json")
orig_save=QFileDialog.getSaveFileName
orig_open=QFileDialog.getOpenFileName
QFileDialog.getSaveFileName=lambda *a,**k:(export_path,"JSON (*.json)")
w.export_profiles()
assert Path(export_path).exists()

# import actual UI method into fresh store
fresh=ProfileStore(root/"fresh.json")
appmod.STORE=fresh
QFileDialog.getOpenFileName=lambda *a,**k:(export_path,"JSON/CSV (*.json *.csv)")
w.import_profiles()
assert len(fresh.load())==2 and fresh.load()[0]["tag"]=="TagA"

QFileDialog.getSaveFileName=orig_save
QFileDialog.getOpenFileName=orig_open
print("PHASE2_UI_ACTIONS_OK",len(fresh.load()))
