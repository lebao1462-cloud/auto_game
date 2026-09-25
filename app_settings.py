from pathlib import Path
from safe_io import atomic_write_json, read_json_with_recovery

class AppSettings:
    SCHEMA_VERSION=1

    def __init__(self,path,base=None):
        self.path=Path(path)
        self.base=Path(base or self.path.parent).resolve()
        self.backups=self.path.parent/"backups"
        self.last_recovery=""

    def defaults(self):
        return {
            "schema_version":self.SCHEMA_VERSION,
            "data_dir":str(self.base/"data"),
            "log_dir":str(self.base/"logs"),
            "tool_dir":str(self.base/"tools"),
            "monitor_interval_sec":30,
            "log_retention_days":14,
        }

    def load(self):
        cfg=self.defaults()
        if self.path.exists():
            try:
                raw,recovered=read_json_with_recovery(self.path,self.backups)
                self.last_recovery=recovered or ""
                if isinstance(raw,dict):
                    version=int(raw.get("schema_version",0) or 0)
                    cfg.update(raw)
                    if version<self.SCHEMA_VERSION:
                        cfg=self._migrate(cfg,version)
                        self.save(cfg)
            except Exception:
                pass
        cfg["schema_version"]=self.SCHEMA_VERSION
        try: cfg["monitor_interval_sec"]=max(10,int(cfg.get("monitor_interval_sec",30)))
        except Exception: cfg["monitor_interval_sec"]=30
        try: cfg["log_retention_days"]=max(1,int(cfg.get("log_retention_days",14)))
        except Exception: cfg["log_retention_days"]=14
        return cfg

    def _migrate(self,cfg,version):
        out=self.defaults(); out.update(cfg or {}); out["schema_version"]=self.SCHEMA_VERSION
        return out

    def save(self,cfg):
        out=self.defaults(); out.update(cfg or {}); out["schema_version"]=self.SCHEMA_VERSION
        atomic_write_json(self.path,out,backup=True,backup_dir=self.backups)
        return out
