import os,sys,tempfile,time,zipfile,json
os.environ["QT_QPA_PLATFORM"]="offscreen"
sys.path.insert(0,r"D:\code\phongthan_proxy_manager")
from pathlib import Path

# module tests: settings, daily log rotation, diagnostics sanitization
from app_settings import AppSettings
from app_log import DailyLogger
from diagnostics import export_diagnostics

root=Path(tempfile.mkdtemp(prefix="pt_phase7_",dir=r"D:\code\phongthan_proxy_manager\data"))
s=AppSettings(root/"cfg.json",root)
cfg=s.save({"monitor_interval_sec":12,"log_retention_days":2})
assert s.load()["monitor_interval_sec"]==12
logdir=root/"logs"; lg=DailyLogger(logdir,2)
today=lg.write("TEST","ok"); assert today.exists()
old=logdir/"app_2000-01-01.log"; old.write_text("old",encoding="utf-8")
os.utime(old,(1,1)); removed=lg.rotate(); assert not old.exists() and removed

dd=root/"data"; dd.mkdir()
(dd/"profiles.json").write_text(json.dumps([{"name":"A","proxy":"socks5://user:secret@1.2.3.4:1080"}]),encoding="utf-8")
diag=export_diagnostics(Path(r"D:\code\phongthan_proxy_manager"),dd,logdir,root/"diag.zip")
assert Path(diag).exists()
with zipfile.ZipFile(diag) as z:
    prof=z.read("profiles_sanitized.json").decode("utf-8")
assert "secret" not in prof and "********" in prof
print("PHASE7_MODULES_OK")

# UI tests on real config/profile but no destructive actions
from PySide6.QtWidgets import QApplication,QMessageBox
from PySide6.QtCore import QSettings
import app as appmod
q=QApplication([])
w=appmod.App()
w.timer.stop(); w.monitor_timer.stop(); w.proxy_retest_timer.stop()
assert w.tabs.count()==4
assert w.tabs.tabText(0)=="Dashboard" and w.tabs.tabText(3)=="Settings"
assert hasattr(w,"verify_all_btn") and hasattr(w,"diag_btn")
assert hasattr(w,"profile_search") and hasattr(w,"profile_filter")
assert hasattr(w,"set_data_dir") and hasattr(w,"save_settings_btn")

# Search filter
w.profile_search.setText("ACC-01")
visible=[i for i in range(w.profile_table.rowCount()) if not w.profile_table.isRowHidden(i)]
assert len(visible)==1 and w.profile_table.item(visible[0],0).text()=="ACC-01"
w.profile_search.clear()

# Save current settings safely (same dirs)
w.set_monitor_interval.setValue(30); w.set_retention.setValue(14); w.save_settings()
assert appmod.SETTINGS_STORE.load()["monitor_interval_sec"]==30

# Geometry persistence capability
geom=w.saveGeometry(); QSettings("PhongThanTools","ProxyManager").setValue("geometry",geom)
assert QSettings("PhongThanTools","ProxyManager").value("geometry") is not None

# confirm dialog prevents dangerous action when No
orig=QMessageBox.question
QMessageBox.question=lambda *a,**k: QMessageBox.StandardButton.No
before=appmod.LAUNCHER._load().copy()
w.stop_all()
after=appmod.LAUNCHER._load().copy()
assert before==after
QMessageBox.question=orig
print("PHASE7_UI_OK",w.tabs.count(),w.profile_table.rowCount())
print("PHASE7_SMOKE_OK")
