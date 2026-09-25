import base64, json
from pathlib import Path
import win32crypt
from safe_io import atomic_write_json, read_json_with_recovery

class CredentialStore:
    def __init__(self,path):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        self.backups=self.path.parent/"backups"

    def _load(self):
        if not self.path.exists(): return {}
        try:
            data,_=read_json_with_recovery(self.path,self.backups)
            return data if isinstance(data,dict) else {}
        except Exception:
            return {}

    def _save(self,data):
        atomic_write_json(self.path,data,backup=True,backup_dir=self.backups)

    def set(self,key,value):
        raw=value.encode("utf-8")
        blob=win32crypt.CryptProtectData(raw,"PhongThanProxy",None,None,None,0)
        data=self._load(); data[str(key)]=base64.b64encode(blob).decode("ascii"); self._save(data)

    def get(self,key,default=""):
        data=self._load(); enc=data.get(str(key))
        if not enc: return default
        try:
            blob=base64.b64decode(enc)
            return win32crypt.CryptUnprotectData(blob,None,None,None,0)[1].decode("utf-8")
        except Exception:
            return default

    def delete(self,key):
        data=self._load()
        if str(key) in data:
            data.pop(str(key),None); self._save(data)

    def retain(self,keys):
        keep={str(k) for k in keys}; data=self._load()
        new={k:v for k,v in data.items() if k in keep}
        if new!=data: self._save(new)
