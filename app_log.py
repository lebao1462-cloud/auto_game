from datetime import datetime, timedelta
from pathlib import Path

class DailyLogger:
    def __init__(self,log_dir,retention_days=14):
        self.log_dir=Path(log_dir); self.log_dir.mkdir(parents=True,exist_ok=True)
        self.retention_days=max(1,int(retention_days))

    def write(self,event,message=""):
        path=self.log_dir/f"app_{datetime.now():%Y-%m-%d}.log"
        with open(path,"a",encoding="utf-8") as f:
            f.write(f"{datetime.now().isoformat(timespec='seconds')}\t{event}\t{message}\n")
        return path

    def rotate(self):
        cutoff=datetime.now()-timedelta(days=self.retention_days)
        removed=[]
        for p in self.log_dir.glob("*.log"):
            try:
                if datetime.fromtimestamp(p.stat().st_mtime)<cutoff:
                    p.unlink(); removed.append(str(p))
            except Exception:
                pass
        for p in self.log_dir.glob("*_events_*.csv"):
            try:
                if datetime.fromtimestamp(p.stat().st_mtime)<cutoff:
                    p.unlink(); removed.append(str(p))
            except Exception:
                pass
        return removed
