import csv, json, sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from PySide6.QtCore import QThread, Signal, QTimer, QSettings
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,
 QPushButton,QPlainTextEdit,QTableWidget,QTableWidgetItem,QLabel,QLineEdit,QFileDialog,
 QMessageBox,QHeaderView,QTabWidget,QComboBox,QSpinBox,QCheckBox)
from proxy_core import test_proxy, masked_proxy
from profile_store import ProfileStore
from game_launcher import GameLauncher
from proxifier_router import apply as apply_routing, active as routing_active, driver_ready, install_proxifier_elevated
from routing_verify import verify_all
from route_guard import RouteGuard
from monitoring import MonitoringEngine
from app_settings import AppSettings
from app_log import DailyLogger
from diagnostics import export_diagnostics
from platform_utils import is_admin
from version import __version__, APP_NAME

BASE=Path(sys.executable).resolve().parent if getattr(sys,"frozen",False) else Path(__file__).resolve().parent
SETTINGS_STORE=AppSettings(BASE/"config.json",BASE)
CFG=SETTINGS_STORE.load()
DATA=Path(CFG["data_dir"]); DATA.mkdir(parents=True,exist_ok=True)
LOGS=Path(CFG["log_dir"]); LOGS.mkdir(parents=True,exist_ok=True)
TOOLS=Path(CFG["tool_dir"]); TOOLS.mkdir(parents=True,exist_ok=True)
STORE=ProfileStore(DATA/"profiles.json")
LAUNCHER=GameLauncher(DATA/"running.json")

class MonitorWorker(QThread):
    result=Signal(object)
    def __init__(self,engine,profiles):
        super().__init__(); self.engine=engine; self.profiles=profiles
    def run(self):
        self.result.emit(self.engine.collect(self.profiles))

class ProxyWorker(QThread):
    result=Signal(object)
    def __init__(self,ps,max_workers=10):
        super().__init__(); self.ps=ps; self.max_workers=max(1,min(max_workers,len(ps) or 1))
    def run(self):
        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            futures={pool.submit(test_proxy,p):p for p in self.ps}
            for fut in as_completed(futures):
                if self.isInterruptionRequested():
                    for f in futures: f.cancel()
                    break
                try: self.result.emit(fut.result())
                except Exception as e:
                    from proxy_core import ProxyResult
                    self.result.emit(ProxyResult(futures[fut],False,error=str(e)[:160]))

class App(QMainWindow):
    def __init__(self):
        super().__init__()
        self.worker=None; self.monitor_worker=None; self.edit_index=None; self.live_proxies=[]
        self.guard=RouteGuard(LOGS); self.monitor_engine=MonitoringEngine(LOGS); self.monitor_snapshot={}
        self.logger=DailyLogger(LOGS,CFG.get("log_retention_days",14)); self.logger.rotate(); self.logger.write("APP_START")
        self.setWindowTitle(f"{APP_NAME} v{__version__}"); self.resize(1180,760)
        qs=QSettings("PhongThanTools","ProxyManager")
        geo=qs.value("geometry")
        if geo: self.restoreGeometry(geo)
        self.tabs=QTabWidget(); self.setCentralWidget(self.tabs)
        self.dashboard_tab=QWidget(); self.proxy_tab=QWidget(); self.profile_tab=QWidget(); self.settings_tab=QWidget()
        self.tabs.addTab(self.dashboard_tab,"Dashboard"); self.tabs.addTab(self.proxy_tab,"Proxy Manager"); self.tabs.addTab(self.profile_tab,"Profiles"); self.tabs.addTab(self.settings_tab,"Settings")
        self.build_dashboard(); self.build_proxy(); self.build_profiles(); self.build_settings(); self.refresh_profiles()
        self.timer=QTimer(self); self.timer.timeout.connect(self.refresh_runtime); self.timer.start(1000)
        self.proxy_retest_timer=QTimer(self); self.proxy_retest_timer.timeout.connect(self.auto_retest_proxy)
        self.monitor_timer=QTimer(self); self.monitor_timer.timeout.connect(self.run_background_monitor); self.monitor_timer.start(int(CFG.get("monitor_interval_sec",30))*1000)
        QTimer.singleShot(1500,self.run_background_monitor)

    def notify(self,message,timeout=5000):
        self.statusBar().showMessage(message,timeout)
        self.logger.write("UI",message)

    def build_dashboard(self):
        l=QVBoxLayout(self.dashboard_tab)
        title=QLabel("Tổng quan hệ thống"); l.addWidget(title)
        row=QHBoxLayout()
        self.d_profiles=QLabel("Profiles: 0")
        self.d_running=QLabel("Running: 0")
        self.d_routed=QLabel("Routed: 0")
        self.d_proxy=QLabel("Proxy LIVE: 0/0")
        self.d_admin=QLabel("Admin: YES" if is_admin() else "Admin: NO")
        for w in (self.d_profiles,self.d_running,self.d_routed,self.d_proxy,self.d_admin): row.addWidget(w)
        row.addStretch(); l.addLayout(row)
        b=QHBoxLayout()
        self.verify_all_btn=QPushButton("Verify All")
        self.diag_btn=QPushButton("Export Diagnostics")
        self.d_launch_all=QPushButton("Launch All")
        self.d_stop_all=QPushButton("Stop All")
        for w in (self.verify_all_btn,self.diag_btn,self.d_launch_all,self.d_stop_all): b.addWidget(w)
        b.addStretch(); l.addLayout(b)
        self.dashboard_detail=QLabel("Sẵn sàng"); l.addWidget(self.dashboard_detail); l.addStretch()
        self.verify_all_btn.clicked.connect(self.verify_all_now)
        self.diag_btn.clicked.connect(self.export_diagnostics_clicked)
        self.d_launch_all.clicked.connect(self.launch_all)
        self.d_stop_all.clicked.connect(self.stop_all)

    def build_settings(self):
        l=QVBoxLayout(self.settings_tab)
        self.set_data_dir=QLineEdit(str(CFG.get("data_dir",DATA)))
        self.set_log_dir=QLineEdit(str(CFG.get("log_dir",LOGS)))
        self.set_tool_dir=QLineEdit(str(CFG.get("tool_dir",TOOLS)))
        rows=[("Data",self.set_data_dir),("Logs",self.set_log_dir),("Tools",self.set_tool_dir)]
        for label,edit in rows:
            h=QHBoxLayout(); h.addWidget(QLabel(label)); h.addWidget(edit)
            btn=QPushButton("Chọn")
            btn.clicked.connect(lambda checked=False,e=edit:self.choose_directory(e))
            h.addWidget(btn); l.addLayout(h)
        h=QHBoxLayout()
        self.set_monitor_interval=QSpinBox(); self.set_monitor_interval.setRange(10,3600); self.set_monitor_interval.setValue(int(CFG.get("monitor_interval_sec",30))); self.set_monitor_interval.setSuffix(" s")
        self.set_retention=QSpinBox(); self.set_retention.setRange(1,365); self.set_retention.setValue(int(CFG.get("log_retention_days",14))); self.set_retention.setSuffix(" ngày")
        h.addWidget(QLabel("Monitor interval")); h.addWidget(self.set_monitor_interval); h.addWidget(QLabel("Log retention")); h.addWidget(self.set_retention); h.addStretch(); l.addLayout(h)
        self.save_settings_btn=QPushButton("Lưu Settings"); l.addWidget(self.save_settings_btn)
        l.addWidget(QLabel("Thay đổi thư mục Data/Logs/Tools sẽ áp dụng đầy đủ sau khi restart tool."))
        l.addStretch()
        self.save_settings_btn.clicked.connect(self.save_settings)

    def choose_directory(self,edit):
        p=QFileDialog.getExistingDirectory(self,"Chọn thư mục",edit.text() or str(BASE))
        if p: edit.setText(p)

    def save_settings(self):
        cfg={
            "data_dir":self.set_data_dir.text().strip(),
            "log_dir":self.set_log_dir.text().strip(),
            "tool_dir":self.set_tool_dir.text().strip(),
            "monitor_interval_sec":self.set_monitor_interval.value(),
            "log_retention_days":self.set_retention.value(),
        }
        SETTINGS_STORE.save(cfg)
        self.monitor_timer.start(self.set_monitor_interval.value()*1000)
        self.logger.retention_days=self.set_retention.value(); self.logger.rotate()
        self.notify("Đã lưu Settings. Thư mục mới sẽ áp dụng đầy đủ sau restart.")

    def verify_all_now(self):
        self.run_background_monitor()
        self.refresh_runtime()
        self.notify("Đã chạy Verify All.")

    def export_diagnostics_clicked(self):
        path,_=QFileDialog.getSaveFileName(self,"Export Diagnostics",str(DATA/"diagnostics.zip"),"ZIP (*.zip)")
        if not path: return
        if not path.lower().endswith(".zip"): path+=".zip"
        try:
            out=export_diagnostics(BASE,DATA,LOGS,path)
            self.notify(f"Đã export diagnostics: {out}")
        except Exception as e:
            QMessageBox.warning(self,"Diagnostics lỗi",str(e))

    def update_dashboard(self,profiles,routes):
        running=sum(1 for p in profiles if LAUNCHER.status(p.get("name",""),p.get("game_path",""))[0])
        routed=sum(1 for x in routes.values() if x.get("status")=="ROUTED")
        live=sum(1 for x in self.monitor_snapshot.values() if x.get("ok"))
        total=len(self.monitor_snapshot)
        self.d_profiles.setText(f"Profiles: {len(profiles)}")
        self.d_running.setText(f"Running: {running}")
        self.d_routed.setText(f"Routed: {routed}")
        self.d_proxy.setText(f"Proxy LIVE: {live}/{total}")
        self.dashboard_detail.setText(f"Running {running}/{len(profiles)} | Routed {routed}/{len(profiles)} | Proxy LIVE {live}/{total}")

    def closeEvent(self,event):
        QSettings("PhongThanTools","ProxyManager").setValue("geometry",self.saveGeometry())
        self.logger.write("APP_CLOSE")
        super().closeEvent(event)

    def build_proxy(self):
        l=QVBoxLayout(self.proxy_tab)
        l.addWidget(QLabel("IP:PORT | IP:PORT:USER:PASS | http://... | socks5://..."))
        self.pinput=QPlainTextEdit(); self.pinput.setMaximumHeight(150); l.addWidget(self.pinput)
        b=QHBoxLayout()
        self.pimport=QPushButton("Import TXT"); self.ptest=QPushButton("Test Proxy")
        self.pstop=QPushButton("Dừng"); self.pexport=QPushButton("Export CSV"); self.pclear=QPushButton("Xóa")
        self.pstop.setEnabled(False)
        for x in (self.pimport,self.ptest,self.pstop,self.pexport,self.pclear): b.addWidget(x)
        l.addLayout(b)
        opts=QHBoxLayout()
        self.pfilter=QComboBox(); self.pfilter.addItems(["ALL","LIVE","DIE"])
        self.pworkers=QSpinBox(); self.pworkers.setRange(1,50); self.pworkers.setValue(10)
        self.pauto=QCheckBox("Auto retest")
        self.pinterval=QSpinBox(); self.pinterval.setRange(30,3600); self.pinterval.setValue(300); self.pinterval.setSuffix(" s")
        for w in (QLabel("Lọc"),self.pfilter,QLabel("Workers"),self.pworkers,self.pauto,QLabel("Chu kỳ"),self.pinterval): opts.addWidget(w)
        opts.addStretch(); l.addLayout(opts)
        self.ptable=QTableWidget(0,5); self.ptable.setHorizontalHeaderLabels(["Proxy","Status","IP đầu ra","Latency","Chi tiết"])
        self.ptable.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.ptable.setSortingEnabled(True); l.addWidget(self.ptable)
        self.pstatus=QLabel("Sẵn sàng"); l.addWidget(self.pstatus)
        self.pimport.clicked.connect(self.import_proxy); self.ptest.clicked.connect(self.test_proxies)
        self.pstop.clicked.connect(self.stop_proxy); self.pexport.clicked.connect(self.export_proxy)
        self.pclear.clicked.connect(lambda:(self.pinput.clear(),self.ptable.setRowCount(0)))
        self.pfilter.currentTextChanged.connect(self.apply_proxy_filter)
        self.pauto.toggled.connect(self.toggle_auto_retest); self.pinterval.valueChanged.connect(self.update_auto_retest_interval)

    def proxy_lines(self):
        seen=set(); out=[]
        for x in self.pinput.toPlainText().splitlines():
            x=x.strip()
            if x and not x.startswith("#") and x not in seen: seen.add(x); out.append(x)
        return out

    def import_proxy(self):
        p,_=QFileDialog.getOpenFileName(self,"Import proxy","","Text (*.txt);;All files (*)")
        if p: self.pinput.setPlainText(Path(p).read_text(encoding="utf-8-sig",errors="replace"))

    def test_proxies(self):
        ps=self.proxy_lines()
        if not ps: self.pstatus.setText("Chưa có proxy."); return
        if self.worker and self.worker.isRunning(): return
        self.ptable.setSortingEnabled(False)
        self.ptable.setRowCount(0); self.live_proxies=[]; self.done=self.live=0; self.total=len(ps)
        self.ptest.setEnabled(False); self.pstop.setEnabled(True)
        self.worker=ProxyWorker(ps,self.pworkers.value()); self.worker.result.connect(self.proxy_result); self.worker.finished.connect(self.proxy_finished); self.worker.start()

    def proxy_result(self,r):
        self.done+=1; self.live+=int(r.ok)
        if r.ok: self.live_proxies.append(r.proxy)
        row=self.ptable.rowCount(); self.ptable.insertRow(row)
        vals=[masked_proxy(r.proxy),"LIVE" if r.ok else "DIE",r.ip if r.ok else "",str(r.latency_ms) if r.ok else "-",r.error if not r.ok else ""]
        for c,v in enumerate(vals):
            item=QTableWidgetItem(v)
            if c==3 and r.ok: item.setData(256,int(r.latency_ms))
            if c==1: self._paint(item,"LIVE" if r.ok else "DIE")
            self.ptable.setItem(row,c,item)
        self.append_proxy_history(r)
        self.apply_proxy_filter()
        self.pstatus.setText(f"{self.done}/{self.total} | LIVE {self.live} | DIE {self.done-self.live}")

    def proxy_finished(self):
        self.ptest.setEnabled(True); self.pstop.setEnabled(False); self.refresh_proxy_combo()
        self.ptable.setSortingEnabled(True); self.apply_proxy_filter()
        self.pstatus.setText(f"Hoàn tất | LIVE {self.live}/{self.done} | Workers {self.pworkers.value()}")

    def stop_proxy(self):
        if self.worker and self.worker.isRunning(): self.worker.requestInterruption()

    def append_proxy_history(self,r):
        path=DATA/"proxy_history.csv"
        new=not path.exists()
        with open(path,"a",newline="",encoding="utf-8-sig") as f:
            w=csv.writer(f)
            if new: w.writerow(["Timestamp","Proxy","Status","Exit IP","Latency ms","Error"])
            w.writerow([datetime.now().isoformat(timespec="seconds"),masked_proxy(r.proxy),"LIVE" if r.ok else "DIE",r.ip,r.latency_ms if r.ok else "",r.error])

    def apply_proxy_filter(self):
        mode=self.pfilter.currentText() if hasattr(self,"pfilter") else "ALL"
        for row in range(self.ptable.rowCount()):
            item=self.ptable.item(row,1)
            status=item.text() if item else ""
            self.ptable.setRowHidden(row,mode!="ALL" and status!=mode)

    def toggle_auto_retest(self,enabled):
        if enabled:
            self.proxy_retest_timer.start(self.pinterval.value()*1000)
            self.pstatus.setText(f"Auto retest bật: {self.pinterval.value()} giây")
        else:
            self.proxy_retest_timer.stop()

    def update_auto_retest_interval(self,value):
        if self.pauto.isChecked(): self.proxy_retest_timer.start(value*1000)

    def auto_retest_proxy(self):
        if self.worker and self.worker.isRunning(): return
        if self.proxy_lines(): self.test_proxies()

    def run_background_monitor(self):
        if self.monitor_worker and self.monitor_worker.isRunning(): return
        ps=STORE.load()
        if not any(p.get("proxy","").strip() for p in ps): return
        self.monitor_worker=MonitorWorker(self.monitor_engine,ps)
        self.monitor_worker.result.connect(self.on_monitor_result)
        self.monitor_worker.start()

    def on_monitor_result(self,snapshot):
        self.monitor_snapshot=snapshot or {}
        live=sum(1 for v in self.monitor_snapshot.values() if v.get("ok"))
        total=len(self.monitor_snapshot)
        if total:
            self.prof_status.setText(f"Monitor proxy: LIVE {live}/{total}")

    def export_proxy(self):
        if not self.ptable.rowCount(): return
        p,_=QFileDialog.getSaveFileName(self,"Export",str(DATA/"proxy_results.csv"),"CSV (*.csv)")
        if p:
            with open(p,"w",newline="",encoding="utf-8-sig") as f:
                w=csv.writer(f); w.writerow(["Proxy","Status","Exit IP","Latency","Detail"])
                for r in range(self.ptable.rowCount()): w.writerow([self.ptable.item(r,c).text() if self.ptable.item(r,c) else "" for c in range(5)])

    def build_profiles(self):
        l=QVBoxLayout(self.profile_tab); f=QHBoxLayout()
        self.name=QLineEdit(); self.name.setPlaceholderText("ACC-01")
        self.proxy_combo=QComboBox(); self.proxy_combo.setEditable(True); self.proxy_combo.setMinimumWidth(280)
        self.game=QLineEdit(); self.game.setPlaceholderText("autoupdate.exe"); self.browse=QPushButton("Chọn Launcher")
        for w in (QLabel("Profile"),self.name,QLabel("Proxy"),self.proxy_combo,QLabel("Game"),self.game,self.browse): f.addWidget(w)
        l.addLayout(f)
        meta=QHBoxLayout()
        self.tag=QLineEdit(); self.tag.setPlaceholderText("ví dụ: Main / Farm / Test")
        self.note=QLineEdit(); self.note.setPlaceholderText("Ghi chú profile")
        self.fail_closed=QCheckBox("Fail-closed"); self.fail_closed.setChecked(True)
        self.auto_reconnect=QCheckBox("Auto reconnect"); self.auto_reconnect.setChecked(True)
        for w in (QLabel("Tag"),self.tag,QLabel("Note"),self.note,self.fail_closed,self.auto_reconnect): meta.addWidget(w)
        l.addLayout(meta)
        b=QHBoxLayout()
        self.save=QPushButton("Thêm Profile"); self.edit=QPushButton("Sửa"); self.delete=QPushButton("Xóa"); self.cancel=QPushButton("Hủy sửa")
        self.clone_btn=QPushButton("Clone"); self.import_profiles_btn=QPushButton("Import"); self.export_profiles_btn=QPushButton("Export")
        for x in (self.save,self.edit,self.delete,self.cancel,self.clone_btn,self.import_profiles_btn,self.export_profiles_btn): b.addWidget(x)
        self.launch_btn=QPushButton("Mở Launcher"); self.adopt_btn=QPushButton("Nhận diện thủ công"); self.stop_btn=QPushButton("Stop"); self.restart_btn=QPushButton("Restart")
        self.launch_all_btn=QPushButton("Launch All"); self.stop_all_btn=QPushButton("Stop All"); self.restart_all_btn=QPushButton("Restart All"); self.route_btn=QPushButton("Áp dụng Routing")
        for x in (self.launch_btn,self.adopt_btn,self.stop_btn,self.restart_btn,self.launch_all_btn,self.stop_all_btn,self.restart_all_btn,self.route_btn): b.addWidget(x)
        l.addLayout(b)
        flt=QHBoxLayout()
        self.profile_search=QLineEdit(); self.profile_search.setPlaceholderText("Tìm profile / tag / note / proxy")
        self.profile_filter=QComboBox(); self.profile_filter.addItems(["ALL","RUNNING","OFFLINE","ROUTED","ERROR"])
        flt.addWidget(QLabel("Search")); flt.addWidget(self.profile_search); flt.addWidget(QLabel("Filter")); flt.addWidget(self.profile_filter)
        l.addLayout(flt)
        self.profile_table=QTableWidget(0,11); self.profile_table.setHorizontalHeaderLabels(["Profile","Tag","Note","Proxy","Game path","Kiểm tra","Game","PID","Routing","Proxy endpoint","Game server"])
        self.profile_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.profile_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows); self.profile_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        l.addWidget(self.profile_table); self.prof_status=QLabel("Sẵn sàng"); l.addWidget(self.prof_status)
        self.browse.clicked.connect(self.choose_game); self.save.clicked.connect(self.save_profile); self.edit.clicked.connect(self.begin_edit)
        self.delete.clicked.connect(self.delete_profile); self.cancel.clicked.connect(self.cancel_edit); self.profile_table.doubleClicked.connect(lambda _:self.begin_edit())
        self.clone_btn.clicked.connect(self.clone_profile); self.import_profiles_btn.clicked.connect(self.import_profiles); self.export_profiles_btn.clicked.connect(self.export_profiles)
        self.launch_btn.clicked.connect(self.launch_selected); self.adopt_btn.clicked.connect(self.adopt_selected); self.stop_btn.clicked.connect(self.stop_selected); self.restart_btn.clicked.connect(self.restart_selected)
        self.launch_all_btn.clicked.connect(self.launch_all); self.stop_all_btn.clicked.connect(self.stop_all); self.restart_all_btn.clicked.connect(self.restart_all)
        self.route_btn.clicked.connect(self.apply_routing_clicked)
        self.profile_search.textChanged.connect(self.apply_profile_filter)
        self.profile_filter.currentTextChanged.connect(self.apply_profile_filter)

    def refresh_proxy_combo(self):
        current=self.proxy_combo.currentText(); self.proxy_combo.clear(); self.proxy_combo.addItem("")
        self.proxy_combo.addItems(self.live_proxies)
        if current: self.proxy_combo.setCurrentText(current)

    def choose_game(self):
        p,_=QFileDialog.getOpenFileName(self,"Chọn launcher","","Executable (*.exe);;All files (*)")
        if p: self.game.setText(p)

    def refresh_profiles(self):
        ps=STORE.load(); self.profile_table.setRowCount(0); counts={}
        for p in ps:
            x=p.get("proxy","").strip()
            if x: counts[x]=counts.get(x,0)+1
        for p in ps:
            row=self.profile_table.rowCount(); self.profile_table.insertRow(row); x=p.get("proxy",""); g=p.get("game_path",""); checks=[]
            if x and counts.get(x,0)>1: checks.append("TRÙNG PROXY")
            if g and not Path(g).exists(): checks.append("GAME KHÔNG TỒN TẠI")
            health=self.monitor_snapshot.get(x) if x else None
            if health:
                if health.get("ok"): checks.append(f"PROXY LIVE {health.get('latency_ms',0)}ms {health.get('ip','')}")
                else: checks.append("PROXY DIE")
            running,pid=LAUNCHER.status(p.get("name",""),g)
            route="CONFIGURED" if routing_active() and x and g else "DIRECT"
            vals=[p.get("name",""),p.get("tag",""),p.get("note",""),masked_proxy(x),g," | ".join(checks) or "OK","RUNNING" if running else "OFFLINE",str(pid or ""),route,"",""]
            for c,v in enumerate(vals): self.profile_table.setItem(row,c,QTableWidgetItem(v))
            self._paint(self.profile_table.item(row,6),"RUNNING" if running else "OFFLINE")
            self._paint(self.profile_table.item(row,8),route)
        self.prof_status.setText(f"{len(ps)} profile")
        self.apply_profile_filter()

    def apply_profile_filter(self):
        if not hasattr(self,"profile_table"): return
        query=self.profile_search.text().strip().lower() if hasattr(self,"profile_search") else ""
        mode=self.profile_filter.currentText() if hasattr(self,"profile_filter") else "ALL"
        for row in range(self.profile_table.rowCount()):
            values=[]
            for c in range(self.profile_table.columnCount()):
                item=self.profile_table.item(row,c)
                values.append(item.text() if item else "")
            text=" ".join(values).lower()
            game=values[6] if len(values)>6 else ""
            route=values[8] if len(values)>8 else ""
            ok_query=(not query or query in text)
            if mode=="ALL": ok_mode=True
            elif mode=="RUNNING": ok_mode=(game=="RUNNING")
            elif mode=="OFFLINE": ok_mode=(game=="OFFLINE")
            elif mode=="ROUTED": ok_mode=(route=="ROUTED")
            else: ok_mode=(route in ("DIRECT","PROXY DOWN","ROUTING ERROR") or "DIE" in values[5] or "CẢNH BÁO" in values[5])
            self.profile_table.setRowHidden(row,not (ok_query and ok_mode))

    @staticmethod
    def _paint(item,state):
        if not item: return
        if state in ("LIVE","RUNNING","ROUTED","OK"):
            item.setBackground(QColor(210,245,220))
        elif state in ("DIE","OFFLINE","DIRECT","PROXY DOWN","ROUTING ERROR"):
            item.setBackground(QColor(255,220,220))
        elif state in ("ROUTING","CONFIGURED"):
            item.setBackground(QColor(255,245,200))

    def selected(self):
        rows=self.profile_table.selectionModel().selectedRows(); return rows[0].row() if rows else None

    def save_profile(self):
        n=self.name.text().strip()
        if not n: QMessageBox.warning(self,"Thiếu","Nhập tên profile."); return
        try:
            new_proxy=self.proxy_combo.currentText().strip()
            new_game=self.game.text().strip()
            old_profile=None
            was_running=False
            if self.edit_index is None:
                STORE.add(n,new_proxy,new_game,self.tag.text().strip(),self.note.text().strip(),self.fail_closed.isChecked(),self.auto_reconnect.isChecked())
            else:
                old_profile=STORE.load()[self.edit_index]
                old_name=old_profile.get("name","")
                was_running=LAUNCHER.status(old_name,old_profile.get("game_path",""))[0]
                STORE.update(self.edit_index,n,new_proxy,new_game,self.tag.text().strip(),self.note.text().strip(),self.fail_closed.isChecked(),self.auto_reconnect.isChecked())
                if old_name and old_name!=n: LAUNCHER.rename_profile(old_name,n)
                proxy_changed=(old_profile.get("proxy","").strip()!=new_proxy)
                game_changed=(old_profile.get("game_path","").strip()!=new_game)
                if proxy_changed or game_changed:
                    apply_routing(STORE.load())
                    if was_running:
                        LAUNCHER.restart(n,new_game)
                        self.prof_status.setText(f"{n}: routing đã cập nhật, launcher đã mở lại để dùng proxy mới.")
        except Exception as e: QMessageBox.warning(self,"Lỗi",str(e)); return
        self.cancel_edit(); self.refresh_profiles()

    def begin_edit(self):
        i=self.selected()
        if i is None: return
        p=STORE.load()[i]; self.edit_index=i; self.name.setText(p.get("name","")); self.proxy_combo.setCurrentText(p.get("proxy","")); self.game.setText(p.get("game_path","")); self.tag.setText(p.get("tag","")); self.note.setText(p.get("note","")); self.fail_closed.setChecked(bool(p.get("fail_closed",True))); self.auto_reconnect.setChecked(bool(p.get("auto_reconnect",True))); self.save.setText("Lưu thay đổi")

    def delete_profile(self):
        i=self.selected()
        if i is not None and QMessageBox.question(self,"Xác nhận","Xóa profile đã chọn?")==QMessageBox.StandardButton.Yes:
            p=STORE.load()[i]
            self.guard.clear(p.get("name",""))
            LAUNCHER.remove_profile(p.get("name",""),stop=False)
            STORE.delete(i); self.cancel_edit(); self.refresh_profiles()

    def clone_profile(self):
        i=self.selected()
        if i is None: return
        try:
            p=STORE.clone(i)
            self.refresh_profiles()
            self.prof_status.setText(f"Đã clone thành {p['name']}")
        except Exception as e:
            QMessageBox.warning(self,"Clone lỗi",str(e))

    def export_profiles(self):
        rows=STORE.safe_export()
        if not rows: return
        path,_=QFileDialog.getSaveFileName(self,"Export profiles",str(DATA/"profiles_export.json"),"JSON (*.json);;CSV (*.csv)")
        if not path: return
        p=Path(path)
        try:
            if p.suffix.lower()==".csv":
                with open(p,"w",newline="",encoding="utf-8-sig") as f:
                    w=csv.DictWriter(f,fieldnames=list(ProfileStore.FIELDS)); w.writeheader(); w.writerows(rows)
            else:
                if p.suffix.lower()!=".json": p=p.with_suffix(".json")
                p.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding="utf-8")
            self.prof_status.setText(f"Đã export {len(rows)} profile")
        except Exception as e:
            QMessageBox.warning(self,"Export lỗi",str(e))

    def import_profiles(self):
        path,_=QFileDialog.getOpenFileName(self,"Import profiles","","JSON/CSV (*.json *.csv);;All files (*)")
        if not path: return
        try:
            p=Path(path)
            if p.suffix.lower()==".csv":
                with open(p,"r",encoding="utf-8-sig",newline="") as f: rows=list(csv.DictReader(f))
            else:
                rows=json.loads(p.read_text(encoding="utf-8-sig"))
                if not isinstance(rows,list): raise ValueError("JSON phải là danh sách profile")
            added,skipped=STORE.merge_import(rows)
            self.refresh_profiles()
            self.prof_status.setText(f"Import: thêm {added}, bỏ qua {skipped}")
        except Exception as e:
            QMessageBox.warning(self,"Import lỗi",str(e))

    def launch_selected(self):
        i=self.selected()
        if i is None: return
        p=STORE.load()[i]
        try:
            r=LAUNCHER.open_launcher(p.get("name",""),p.get("game_path",""))
            if r.get("already_running"): self.prof_status.setText(f"{p['name']} đang RUNNING PID {r['pid']}")
            else: self.prof_status.setText(f"Đã mở launcher {p['name']}. Tool sẽ tự nhận diện game.exe khi vào game.")
        except Exception as e: QMessageBox.warning(self,"Launch lỗi",str(e))

    def adopt_selected(self):
        i=self.selected()
        if i is None: return
        p=STORE.load()[i]
        used=set(LAUNCHER._load().values())
        expected=LAUNCHER.expected_game_path(p.get("game_path",""))
        candidates=sorted(pid for pid,path in LAUNCHER._game_processes().items() if pid not in used and (path or "").lower()==expected)
        if not candidates:
            QMessageBox.warning(self,"Không tìm thấy","Không có game.exe đúng đường dẫn profile chưa được gắn.")
            return
        try:
            pid=candidates[-1]; LAUNCHER.adopt(p["name"],pid,p.get("game_path","")); self.refresh_profiles()
            self.prof_status.setText(f"Đã gắn {p['name']} với game.exe PID {pid}")
        except Exception as e: QMessageBox.warning(self,"Nhận diện lỗi",str(e))

    def stop_selected(self):
        i=self.selected()
        if i is not None:
            p=STORE.load()[i]; self.guard.clear(p["name"]); LAUNCHER.stop(p["name"]); self.refresh_profiles()
            self.prof_status.setText(f"Đã stop {p['name']}")

    def restart_selected(self):
        i=self.selected()
        if i is None: return
        p=STORE.load()[i]
        try:
            self.guard.clear(p.get("name","")); LAUNCHER.restart(p.get("name",""),p.get("game_path",""))
            self.prof_status.setText(f"Đã restart {p['name']}: launcher đã mở lại, chờ đăng nhập.")
            self.refresh_profiles()
        except Exception as e:
            QMessageBox.warning(self,"Restart lỗi",str(e))

    def launch_all(self):
        ps=STORE.load(); opened=0; running=0; errors=[]
        for p in ps:
            try:
                r=LAUNCHER.open_launcher(p.get("name",""),p.get("game_path",""))
                running+=int(bool(r.get("already_running"))); opened+=int(not r.get("already_running"))
            except Exception as e:
                errors.append(f"{p.get('name','')}: {e}")
        self.prof_status.setText(f"Launch All: mở {opened}, đang chạy {running}, lỗi {len(errors)}")
        if errors: QMessageBox.warning(self,"Launch All","\n".join(errors[:10]))

    def stop_all(self):
        if QMessageBox.question(self,"Xác nhận","Dừng toàn bộ client đang chạy?")!=QMessageBox.StandardButton.Yes: return
        ps=STORE.load()
        for p in ps: self.guard.clear(p.get("name",""))
        stopped=LAUNCHER.stop_all(ps)
        self.refresh_profiles()
        msg=f"Stop All: đã dừng {len(stopped)} client"; self.prof_status.setText(msg); self.notify(msg)

    def restart_all(self):
        if QMessageBox.question(self,"Xác nhận","Restart toàn bộ client? Các game đang chạy sẽ bị đóng.")!=QMessageBox.StandardButton.Yes: return
        ps=STORE.load(); restarted=0; errors=[]
        for p in ps:
            try:
                self.guard.clear(p.get("name","")); LAUNCHER.restart(p.get("name",""),p.get("game_path","")); restarted+=1
            except Exception as e:
                errors.append(f"{p.get('name','')}: {e}")
        self.refresh_profiles()
        msg=f"Restart All: {restarted} launcher, lỗi {len(errors)}"; self.prof_status.setText(msg); self.notify(msg)
        if errors: QMessageBox.warning(self,"Restart All","\n".join(errors[:10]))

    def apply_routing_clicked(self):
        try:
            if not driver_ready():
                ans=QMessageBox.question(self,"Cần quyền Administrator","Proxifier driver chưa chạy. Mở installer bằng quyền Administrator?")
                if ans==QMessageBox.StandardButton.Yes:
                    if install_proxifier_elevated():
                        self.notify("Đã mở Proxifier installer với quyền Administrator. Sau khi cài xong hãy Apply Routing lại.")
                    else:
                        QMessageBox.warning(self,"Elevation","Không thể mở installer với quyền Administrator.")
                return
            path=apply_routing(STORE.load())
            self.prof_status.setText(f"Routing ACTIVE: {path}"); self.notify("Đã áp dụng routing.")
            self.refresh_profiles()
        except Exception as e:
            QMessageBox.warning(self,"Routing lỗi",str(e))

    def refresh_runtime(self):
        ps=STORE.load()
        LAUNCHER.reconcile(ps)
        if self.profile_table.rowCount()!=len(ps):
            self.refresh_profiles(); return
        routes=verify_all(ps,LAUNCHER)
        proxifier_ok=routing_active()
        proxy_counts={}
        for p in ps:
            raw=p.get("proxy","").strip()
            if raw: proxy_counts[raw]=proxy_counts.get(raw,0)+1
        for row,p in enumerate(ps):
            name=p.get("name","")
            info=routes.get(name,{})
            action=self.guard.observe(p,info,proxifier_ok,LAUNCHER)
            running,pid=LAUNCHER.status(name,p.get("game_path",""))
            status=info.get("status","OFFLINE")
            if action.get("action")=="STOPPED":
                running=False; pid=None
                self.prof_status.setText(f"FAIL-CLOSED: đã dừng {name} vì {action.get('reason','routing lỗi')}.")
            elif action.get("action")=="RELAUNCH":
                status="ROUTING"
                self.prof_status.setText(f"AUTO RECONNECT: proxy {name} đã LIVE, launcher đã mở lại.")
            elif action.get("action")=="RECOVERED":
                self.prof_status.setText(f"{name}: routing đã phục hồi.")
            checks=[]
            raw=p.get("proxy","").strip()
            game_path=p.get("game_path","").strip()
            if raw and proxy_counts.get(raw,0)>1: checks.append("TRÙNG PROXY")
            if game_path and not Path(game_path).exists(): checks.append("GAME KHÔNG TỒN TẠI")
            health=self.monitor_snapshot.get(raw) if raw else None
            if health:
                if health.get("ok"): checks.append(f"PROXY LIVE {health.get('latency_ms',0)}ms {health.get('ip','')}")
                else: checks.append("PROXY DIE")
            if raw and status=="DIRECT": checks.append("CẢNH BÁO DIRECT")
            elif status=="PROXY DOWN": checks.append("PROXY DOWN")
            elif status=="ROUTING ERROR": checks.append("ROUTING ERROR")
            self.profile_table.setItem(row,5,QTableWidgetItem(" | ".join(checks) or "OK"))
            self.profile_table.setItem(row,6,QTableWidgetItem("RUNNING" if running else "OFFLINE"))
            self.profile_table.setItem(row,7,QTableWidgetItem(str(pid or "")))
            self.profile_table.setItem(row,8,QTableWidgetItem(status))
            self.profile_table.setItem(row,9,QTableWidgetItem(info.get("proxy_endpoint","")))
            self.profile_table.setItem(row,10,QTableWidgetItem(info.get("game_server","")))
            self._paint(self.profile_table.item(row,6),"RUNNING" if running else "OFFLINE")
            self._paint(self.profile_table.item(row,8),status)
        self.apply_profile_filter()
        self.update_dashboard(ps,routes)

    def cancel_edit(self):
        self.edit_index=None; self.name.clear(); self.proxy_combo.setCurrentText(""); self.game.clear(); self.tag.clear(); self.note.clear(); self.fail_closed.setChecked(True); self.auto_reconnect.setChecked(True); self.save.setText("Thêm Profile")

if __name__=="__main__":
    app=QApplication(sys.argv); w=App(); w.show(); sys.exit(app.exec())
