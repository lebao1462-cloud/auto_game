import ctypes, sys
from pathlib import Path

def is_admin():
    try: return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception: return False

def restart_elevated():
    if getattr(sys,"frozen",False):
        exe=sys.executable; params=""
    else:
        exe=sys.executable
        script=str(Path(sys.argv[0]).resolve())
        params=f'"{script}"'
    rc=ctypes.windll.shell32.ShellExecuteW(None,"runas",exe,params,None,1)
    return int(rc)>32
