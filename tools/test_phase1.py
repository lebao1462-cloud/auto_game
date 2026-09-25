import os,sys
os.environ["QT_QPA_PLATFORM"]="offscreen"
sys.path.insert(0,r"D:\code\phongthan_proxy_manager")
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QEventLoop,QTimer
from app import App
app=QApplication([])
w=App()
w.pinput.setPlainText("socks5://14.225.204.32:10800\nsocks5://160.187.0.89:1080")
w.pworkers.setValue(2)
loop=QEventLoop()
def done():
    print("ROWS",w.ptable.rowCount())
    print("LIVE",w.live)
    print("HISTORY",os.path.exists(r"D:\code\phongthan_proxy_manager\data\proxy_history.csv"))
    loop.quit()
w.test_proxies()
w.worker.finished.connect(done)
QTimer.singleShot(20000,loop.quit)
loop.exec()
assert w.ptable.rowCount()==2
assert os.path.exists(r"D:\code\phongthan_proxy_manager\data\proxy_history.csv")
w.pfilter.setCurrentText("LIVE")
visible=sum(not w.ptable.isRowHidden(i) for i in range(w.ptable.rowCount()))
print("VISIBLE_LIVE",visible)
w.pauto.setChecked(True)
assert w.proxy_retest_timer.isActive()
w.pauto.setChecked(False)
assert not w.proxy_retest_timer.isActive()
print("PHASE1_SMOKE_OK")
