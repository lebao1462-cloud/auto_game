import json, platform, shutil, tempfile
from datetime import datetime
from pathlib import Path
from profile_store import ProfileStore

def export_diagnostics(base,data_dir,log_dir,out_path=None):
    base=Path(base); data_dir=Path(data_dir); log_dir=Path(log_dir)
    out=Path(out_path) if out_path else data_dir/f"diagnostics_{datetime.now():%Y%m%d_%H%M%S}.zip"
    tmp=Path(tempfile.mkdtemp(prefix="pt_diag_",dir=str(data_dir)))
    try:
        sysinfo={
            "timestamp":datetime.now().isoformat(timespec="seconds"),
            "platform":platform.platform(),
            "python":platform.python_version(),
        }
        (tmp/"system.json").write_text(json.dumps(sysinfo,ensure_ascii=False,indent=2),encoding="utf-8")
        try:
            profiles=ProfileStore(data_dir/"profiles.json").safe_export()
        except Exception as e:
            profiles=[{"error":str(e)}]
        (tmp/"profiles_sanitized.json").write_text(json.dumps(profiles,ensure_ascii=False,indent=2),encoding="utf-8")
        for name in ("PLAN.md","requirements.txt","config.json"):
            src=base/name
            if src.exists(): shutil.copy2(src,tmp/name)
        for name in ("running.json","routing_active.ppx"):
            src=data_dir/name
            if src.exists(): shutil.copy2(src,tmp/name)
        ldst=tmp/"logs"; ldst.mkdir(exist_ok=True)
        if log_dir.exists():
            for src in sorted(log_dir.rglob("*")):
                if src.is_file() and src.stat().st_size<=5*1024*1024:
                    rel=src.relative_to(log_dir); dst=ldst/rel; dst.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(src,dst)
        out.parent.mkdir(parents=True,exist_ok=True)
        archive=shutil.make_archive(str(out.with_suffix("")),"zip",tmp)
        return archive
    finally:
        shutil.rmtree(tmp,ignore_errors=True)
