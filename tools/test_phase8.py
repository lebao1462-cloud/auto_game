import sys,tempfile,json
sys.path.insert(0,r"D:\code\phongthan_proxy_manager")
from pathlib import Path
from profile_store import ProfileStore
from app_settings import AppSettings
from proxifier_router import build_profile

root=Path(tempfile.mkdtemp(prefix="pt_phase8_",dir=r"D:\code\phongthan_proxy_manager\data"))
data=root/"data"; data.mkdir()

# Legacy profile with plaintext auth -> automatic schema migration + DPAPI
pf=data/"profiles.json"
legacy=[{"name":"AUTH","proxy":"socks5://user:SECRET_PASS@1.2.3.4:1080","game_path":r"D:\x\autoupdate.exe","tag":"","note":""}]
pf.write_text(json.dumps(legacy),encoding="utf-8")
s=ProfileStore(pf)
rows=s.load()
assert rows[0]["proxy"]=="socks5://user:SECRET_PASS@1.2.3.4:1080"
disk=pf.read_text(encoding="utf-8")
sec=(data/"secrets.json").read_text(encoding="utf-8")
assert '"schema_version": 2' in disk
assert "SECRET_PASS" not in disk and "SECRET_PASS" not in sec
assert "user:SECRET_PASS" not in disk
assert s.safe_export()[0]["proxy"]=="socks5://1.2.3.4:1080"
assert list((data/"backups").glob("profiles_*.bak"))
print("DPAPI_MIGRATION_OK")

# JSON recovery from backup
s.save(rows)  # creates a known-good v2 backup
pf.write_text("{broken json",encoding="utf-8")
recovered=s.load()
assert recovered and recovered[0]["name"]=="AUTH"
assert s.last_recovery
print("PROFILE_RECOVERY_OK")

# App config schema + backup/recovery
cfgfile=root/"config.json"
aset=AppSettings(cfgfile,root)
aset.save({"monitor_interval_sec":20})
aset.save({"monitor_interval_sec":25})
cfgfile.write_text("{bad",encoding="utf-8")
cfg=aset.load()
assert cfg["schema_version"]==aset.SCHEMA_VERSION and cfg["monitor_interval_sec"] in (20,25)
assert aset.last_recovery
print("CONFIG_RECOVERY_OK")

# Routing config atomic backup
out=data/"routing.ppx"
profiles=[{"name":"T","proxy":"socks5://14.225.204.32:10800","game_path":r"D:\code\phongthan_proxy_manager\data\phase3_test\A\launcher.exe"}]
build_profile(profiles,out)
build_profile(profiles,out)
assert out.exists() and list((data/"backups").glob("routing_*.bak"))
assert not out.with_suffix(out.suffix+".tmp").exists()
print("ROUTING_BACKUP_ATOMIC_OK")

print("PHASE8_SMOKE_OK")
