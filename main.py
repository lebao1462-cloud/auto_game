import csv, sys
from pathlib import Path
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,
 QPushButton,QPlainTextEdit,QTableWidget,QTableWidgetItem,QLabel,QFileDialog,QHeaderView)
from proxy_core import test_proxy, masked_proxy

BASE=Path(__file__).resolve().parent
DATA=BASE/"data"; LOGS=BASE/"logs"
DATA.mkdir(exist_ok=True); LOGS.mkdir(exist_ok=True)

class Worker(QThread):
    result=Signal(object)
    def __init__(self,proxies): super().__init__(); self.proxies=proxies
    def run(self):
        for p in self.proxies:
            if self.isInterruptionRequested(): break
            self.result.emit(test_proxy(p))

class Window(QMainWindow):
    def __init__(self):
        super().__init__(); self.worker=None
        self.setWindowTitle("Phong Than Proxy Manager - Phase 1"); self.resize(980,640)
        root=QWidget(); self.setCentralWidget(root); layout=QVBoxLayout(root)
        layout.addWidget(QLabel("Proxy: IP:PORT | IP:PORT:USER:PASS | http://... | socks5://..."))
        self.input=QPlainTextEdit(); self.input.setMaximumHeight(150)
        self.input.setPlaceholderText("Mỗi dòng một proxy. Password sẽ được ẩn trong bảng kết quả.")
        layout.addWidget(self.input)
        bar=QHBoxLayout()
        self.import_btn=QPushButton("Import TXT"); self.test_btn=QPushButton("Test Proxy")
        self.stop_btn=QPushButton("Dừng"); self.export_btn=QPushButton("Export CSV")
        self.clear_btn=QPushButton("Xóa")
        self.stop_btn.setEnabled(False)
        for b in (self.import_btn,self.test_btn,self.stop_btn,self.export_btn,self.clear_btn): bar.addWidget(b)
        layout.addLayout(bar)
        self.table=QTableWidget(0,5)
        self.table.setHorizontalHeaderLabels(["Proxy","Trạng thái","IP đầu ra","Độ trễ (ms)","Chi tiết"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)
        self.status=QLabel("Sẵn sàng"); layout.addWidget(self.status)
        self.import_btn.clicked.connect(self.import_txt); self.test_btn.clicked.connect(self.start_test)
        self.stop_btn.clicked.connect(self.stop_test); self.export_btn.clicked.connect(self.export_csv)
        self.clear_btn.clicked.connect(self.clear_all)

    def proxies(self):
        seen=set(); out=[]
        for line in self.input.toPlainText().splitlines():
            p=line.strip()
            if p and not p.startswith("#") and p not in seen: seen.add(p); out.append(p)
        return out

    def import_txt(self):
        path,_=QFileDialog.getOpenFileName(self,"Chọn proxy","","Text (*.txt);;All files (*)")
        if path:
            self.input.setPlainText(Path(path).read_text(encoding="utf-8-sig",errors="replace"))

    def start_test(self):
        ps=self.proxies()
        if not ps: self.status.setText("Chưa có proxy."); return
        self.table.setRowCount(0); self.test_btn.setEnabled(False); self.stop_btn.setEnabled(True)
        self.status.setText(f"Đang test 0/{len(ps)} proxy...")
        self.total=len(ps); self.done=0; self.live=0
        self.worker=Worker(ps); self.worker.result.connect(self.add_result)
        self.worker.finished.connect(self.finished); self.worker.start()

    def add_result(self,r):
        self.done+=1; self.live+=int(r.ok); row=self.table.rowCount(); self.table.insertRow(row)
        vals=[masked_proxy(r.proxy),"LIVE" if r.ok else "DIE",r.ip if r.ok else "",
              str(r.latency_ms) if r.ok else "-", "" if r.ok else r.error]
        for c,v in enumerate(vals): self.table.setItem(row,c,QTableWidgetItem(v))
        self.status.setText(f"Đang test {self.done}/{self.total} | LIVE {self.live} | DIE {self.done-self.live}")

    def stop_test(self):
        if self.worker and self.worker.isRunning():
            self.worker.requestInterruption(); self.status.setText("Đang dừng...")

    def finished(self):
        self.test_btn.setEnabled(True); self.stop_btn.setEnabled(False)
        self.status.setText(f"Hoàn tất {self.done}/{self.total} | LIVE {self.live} | DIE {self.done-self.live}")

    def export_csv(self):
        if not self.table.rowCount(): self.status.setText("Chưa có kết quả để export."); return
        path,_=QFileDialog.getSaveFileName(self,"Lưu kết quả",str(DATA/"proxy_results.csv"),"CSV (*.csv)")
        if not path: return
        with open(path,"w",newline="",encoding="utf-8-sig") as f:
            w=csv.writer(f); w.writerow(["Proxy","Status","Exit IP","Latency ms","Detail"])
            for r in range(self.table.rowCount()):
                w.writerow([self.table.item(r,c).text() if self.table.item(r,c) else "" for c in range(5)])
        self.status.setText(f"Đã lưu: {path}")

    def clear_all(self):
        self.input.clear(); self.table.setRowCount(0); self.status.setText("Đã xóa.")

if __name__=="__main__":
    app=QApplication(sys.argv); w=Window(); w.show(); sys.exit(app.exec())
