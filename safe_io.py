import json, shutil
from datetime import datetime
from pathlib import Path

def backup_file(path, backup_dir=None, prefix=None):
    path=Path(path)
    if not path.exists(): return None
    bdir=Path(backup_dir or path.parent/"backups"); bdir.mkdir(parents=True,exist_ok=True)
    name=prefix or path.stem
    dst=bdir/f"{name}_{datetime.now():%Y%m%d_%H%M%S_%f}{path.suffix}.bak"
    shutil.copy2(path,dst)
    return dst

def atomic_write_text(path,text,encoding="utf-8",backup=False,backup_dir=None):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    if backup and path.exists(): backup_file(path,backup_dir)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(text,encoding=encoding)
    tmp.replace(path)
    return path

def atomic_write_json(path,obj,backup=False,backup_dir=None):
    return atomic_write_text(path,json.dumps(obj,ensure_ascii=False,indent=2),backup=backup,backup_dir=backup_dir)

def read_json_with_recovery(path,backup_dir=None):
    path=Path(path)
    if not path.exists(): return None,None
    try:
        return json.loads(path.read_text(encoding="utf-8-sig")),None
    except Exception as first:
        bdir=Path(backup_dir or path.parent/"backups")
        candidates=sorted(bdir.glob(f"{path.stem}_*{path.suffix}.bak"),key=lambda p:p.stat().st_mtime,reverse=True) if bdir.exists() else []
        for b in candidates:
            try:
                data=json.loads(b.read_text(encoding="utf-8-sig"))
                atomic_write_text(path,b.read_text(encoding="utf-8-sig"),backup=False)
                return data,str(b)
            except Exception:
                continue
        raise first
