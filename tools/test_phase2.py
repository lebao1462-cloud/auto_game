import os,sys,tempfile,json,csv
os.environ["QT_QPA_PLATFORM"]="offscreen"
sys.path.insert(0,r"D:\code\phongthan_proxy_manager")
from pathlib import Path
from profile_store import ProfileStore

root=Path(tempfile.mkdtemp(prefix="pt_phase2_",dir=r"D:\code\phongthan_proxy_manager\data"))
s=ProfileStore(root/"profiles.json")
s.add("A","socks5://1.2.3.4:1080",r"D:\A\autoupdate.exe","Main","note A")
s.add("B","","","Farm","note B")
rows=s.load()
assert rows[0]["tag"]=="Main" and rows[0]["note"]=="note A"
s.update(1,"B2","http://5.6.7.8:8080",r"D:\B\autoupdate.exe","Test","edited")
assert s.load()[1]["name"]=="B2" and s.load()[1]["tag"]=="Test"
cl=s.clone(0)
assert cl["name"].startswith("A Copy") and cl["note"]=="note A"
added,skipped=s.merge_import([
 {"name":"C","proxy":"socks5://9.9.9.9:1080","tag":"Imported","note":"ok"},
 {"name":"A","proxy":"duplicate"}
])
assert (added,skipped)==(1,1)
assert len(s.load())==4
# JSON export/import-equivalent
exp=root/"export.json"; exp.write_text(json.dumps(s.load(),ensure_ascii=False,indent=2),encoding="utf-8")
s2=ProfileStore(root/"imported.json"); a,b=s2.merge_import(json.loads(exp.read_text(encoding="utf-8")))
assert a==4 and b==0 and s2.load()[2]["name"].startswith("A Copy")
# CSV export/import-equivalent
csvp=root/"export.csv"
with open(csvp,"w",newline="",encoding="utf-8-sig") as f:
    w=csv.DictWriter(f,fieldnames=list(ProfileStore.FIELDS)); w.writeheader(); w.writerows(s.load())
with open(csvp,"r",encoding="utf-8-sig",newline="") as f: rr=list(csv.DictReader(f))
s3=ProfileStore(root/"csv_import.json"); a,b=s3.merge_import(rr)
assert a==4 and s3.load()[0]["tag"]=="Main"

from PySide6.QtWidgets import QApplication
from app import App
q=QApplication([])
w=App()
assert w.profile_table.columnCount()==9
assert hasattr(w,"clone_btn") and hasattr(w,"import_profiles_btn") and hasattr(w,"export_profiles_btn")
assert hasattr(w,"tag") and hasattr(w,"note")
print("PHASE2_STORE_OK",len(s.load()))
print("PHASE2_UI_OK",w.profile_table.columnCount())
print("PHASE2_SMOKE_OK")
