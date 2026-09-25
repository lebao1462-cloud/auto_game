import os,sys
os.environ["QT_QPA_PLATFORM"]="offscreen"
sys.path.insert(0,r"D:\code\phongthan_proxy_manager")
from PySide6.QtWidgets import QApplication,QMessageBox
import app as appmod

q=QApplication([])
w=appmod.App()
w.timer.stop(); w.monitor_timer.stop(); w.proxy_retest_timer.stop()

called={"elevated":0}
appmod.driver_ready=lambda:False
appmod.install_proxifier_elevated=lambda: called.__setitem__("elevated",called["elevated"]+1) or True
orig=QMessageBox.question
QMessageBox.question=lambda *a,**k: QMessageBox.StandardButton.Yes
w.apply_routing_clicked()
QMessageBox.question=orig
assert called["elevated"]==1
print("ELEVATION_UI_OK")
