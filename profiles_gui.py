import sys
from pathlib import Path
from PySide6.QtWidgets import (QApplication,QMainWindow,QWidget,QVBoxLayout,QHBoxLayout,
 QPushButton,QTableWidget,QTableWidgetItem,QLabel,QLineEdit,QFileDialog,QMessageBox,QHeaderView)
from profile_store import ProfileStore

BASE=Path(__file__).resolve().parent
STORE=ProfileStore(BASE/"data"/"profiles.json")

class Window(QMainWindow):
    def __init__(self):
        super().__init__(); self.edit_index=None
        self.setWindowTitle("Phong Than Manager - Phase 2 Profiles"); self.resize(1050,620)
        root=QWidget(); self.setCentralWidget(root); lay=QVBoxLayout(root)
        form=QHBoxLayout()
        self.name=QLineEdit(); self.name.setPlaceholderText("ACC-01")
        self.proxy=QLineEdit(); self.proxy.setPlaceholderText("socks5://IP:PORT hoặc IP:PORT:USER:PASS")
        self.game=QLineEdit(); self.game.setPlaceholderText("Đường dẫn PhongThan.exe")
        self.browse=QPushButton("Chọn Game")
        for w in (QLabel("Profile"),self.name,QLabel("Proxy"),self.proxy,QLabel("Game"),self.game,self.browse): form.addWidget(w)
        lay.addLayout(form)
        bar=QHBoxLayout()
        self.save=QPushButton("Thêm Profile"); self.edit=QPushButton("Sửa")
        self.delete=QPushButton("Xóa"); self.cancel=QPushButton("Hủy sửa")
        self.reload=QPushButton("Tải lại")
        for b in (self.save,self.edit,self.delete,self.cancel,self.reload): bar.addWidget(b)
        lay.addLayout(bar)
        self.table=QTableWidget(0,4)
        self.table.setHorizontalHeaderLabels(["Profile","Proxy","Game path","Kiểm tra"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        lay.addWidget(self.table)
        self.status=QLabel("Sẵn sàng"); lay.addWidget(self.status)
        self.browse.clicked.connect(self.choose_game); self.save.clicked.connect(self.save_profile)
        self.edit.clicked.connect(self.begin_edit); self.delete.clicked.connect(self.delete_profile)
        self.cancel.clicked.connect(self.cancel_edit); self.reload.clicked.connect(self.refresh)
        self.table.doubleClicked.connect(lambda _idx:self.begin_edit())
        self.refresh()

    def choose_game(self):
        p,_=QFileDialog.getOpenFileName(self,"Chọn file game","","Executable (*.exe);;All files (*)")
        if p: self.game.setText(p)

    def refresh(self):
        ps=STORE.load(); self.table.setRowCount(0)
        assigned={}
        for p in ps:
            proxy=p.get("proxy","").strip()
            if proxy: assigned[proxy]=assigned.get(proxy,0)+1
        for p in ps:
            row=self.table.rowCount(); self.table.insertRow(row)
            proxy=p.get("proxy",""); game=p.get("game_path","")
            check=[]
            if proxy and assigned.get(proxy,0)>1: check.append("TRÙNG PROXY")
            if game and not Path(game).exists(): check.append("GAME KHÔNG TỒN TẠI")
            vals=[p.get("name",""),proxy,game," | ".join(check) or "OK"]
            for c,v in enumerate(vals): self.table.setItem(row,c,QTableWidgetItem(v))
        self.status.setText(f"{len(ps)} profile")

    def save_profile(self):
        name=self.name.text().strip()
        if not name: QMessageBox.warning(self,"Thiếu dữ liệu","Hãy nhập tên profile."); return
        try:
            if self.edit_index is None: STORE.add(name,self.proxy.text().strip(),self.game.text().strip())
            else: STORE.update(self.edit_index,name,self.proxy.text().strip(),self.game.text().strip())
        except Exception as e: QMessageBox.warning(self,"Không thể lưu",str(e)); return
        self.cancel_edit(); self.refresh()

    def selected(self):
        rows=self.table.selectionModel().selectedRows()
        return rows[0].row() if rows else None

    def begin_edit(self):
        i=self.selected()
        if i is None: self.status.setText("Hãy chọn một profile."); return
        p=STORE.load()[i]; self.edit_index=i
        self.name.setText(p.get("name","")); self.proxy.setText(p.get("proxy","")); self.game.setText(p.get("game_path",""))
        self.save.setText("Lưu thay đổi"); self.status.setText(f"Đang sửa {p.get('name','')}")

    def delete_profile(self):
        i=self.selected()
        if i is None: self.status.setText("Hãy chọn một profile."); return
        p=STORE.load()[i]
        if QMessageBox.question(self,"Xác nhận",f"Xóa profile {p.get('name','')}?")==QMessageBox.StandardButton.Yes:
            STORE.delete(i); self.cancel_edit(); self.refresh()

    def cancel_edit(self):
        self.edit_index=None; self.name.clear(); self.proxy.clear(); self.game.clear(); self.save.setText("Thêm Profile")

if __name__=="__main__":
    app=QApplication(sys.argv); w=Window(); w.show(); sys.exit(app.exec())
