import json
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, quote, unquote

from credential_store import CredentialStore
from safe_io import atomic_write_json, read_json_with_recovery

class ProfileStore:
    SCHEMA_VERSION=2
    FIELDS=("name","proxy","game_path","tag","note","fail_closed","auto_reconnect")

    def __init__(self, path):
        self.path=Path(path); self.path.parent.mkdir(parents=True,exist_ok=True)
        self.backups=self.path.parent/"backups"
        self.credentials=CredentialStore(self.path.parent/"secrets.json")
        self.last_recovery=""

    @staticmethod
    def _bool(v, default=False):
        if isinstance(v,bool): return v
        if v is None or v=="": return default
        return str(v).strip().lower() in ("1","true","yes","on","y")

    @classmethod
    def normalize(cls,p):
        p=p or {}
        return {
            "name":str(p.get("name","") or ""),
            "proxy":str(p.get("proxy","") or ""),
            "game_path":str(p.get("game_path","") or ""),
            "tag":str(p.get("tag","") or ""),
            "note":str(p.get("note","") or ""),
            "fail_closed":cls._bool(p.get("fail_closed"), True),
            "auto_reconnect":cls._bool(p.get("auto_reconnect"), True),
        }

    @staticmethod
    def _split_auth(raw):
        raw=(raw or "").strip()
        if not raw: return raw,None
        if "://" not in raw:
            parts=raw.split(":")
            if len(parts)==4:
                host,port,user,password=parts
                return f"http://{host}:{port}",{"username":user,"password":password}
            return raw,None
        try:
            u=urlsplit(raw)
            if u.username is None or u.password is None:
                return raw,None
            host=u.hostname or ""
            if ":" in host and not host.startswith("["): host=f"[{host}]"
            netloc=host+(f":{u.port}" if u.port else "")
            base=urlunsplit((u.scheme,netloc,u.path,u.query,u.fragment))
            return base,{"username":unquote(u.username),"password":unquote(u.password)}
        except Exception:
            return raw,None

    @staticmethod
    def _restore_auth(base,cred):
        if not cred: return base
        try:
            if "://" not in base:
                return base
            u=urlsplit(base)
            user=quote(str(cred.get("username","")),safe="")
            password=quote(str(cred.get("password","")),safe="")
            auth=f"{user}:{password}@"
            return urlunsplit((u.scheme,auth+u.netloc,u.path,u.query,u.fragment))
        except Exception:
            return base

    def _runtime_from_disk(self,p):
        q=dict(p or {})
        sid=q.get("proxy_secret_id","")
        base=str(q.get("proxy","") or "")
        if sid:
            secret=self.credentials.get(sid,"")
            try: cred=json.loads(secret) if secret else None
            except Exception: cred=None
            q["proxy"]=self._restore_auth(base,cred)
        return self.normalize(q)

    def _disk_from_runtime(self,p):
        q=self.normalize(p)
        base,cred=self._split_auth(q["proxy"])
        disk={k:q[k] for k in self.FIELDS if k!="proxy"}
        disk["proxy"]=base
        sid=""
        if cred and cred.get("password")!="":
            sid=f"proxy:{q['name']}"
            self.credentials.set(sid,json.dumps(cred,ensure_ascii=False))
            disk["proxy_secret_id"]=sid
        return disk,sid

    def load(self):
        if not self.path.exists(): return []
        try:
            data,recovered=read_json_with_recovery(self.path,self.backups)
            self.last_recovery=recovered or ""
        except Exception:
            return []
        legacy=isinstance(data,list)
        if legacy:
            profiles=[self.normalize(p) for p in data if isinstance(p,dict)]
            # Automatic migration from legacy list to schema v2.
            self.save(profiles)
            return profiles
        if not isinstance(data,dict): return []
        version=int(data.get("schema_version",1) or 1)
        rows=data.get("profiles",[])
        if not isinstance(rows,list): return []
        profiles=[self._runtime_from_disk(p) for p in rows if isinstance(p,dict)]
        if version<self.SCHEMA_VERSION:
            self.save(profiles)
        return profiles

    def save(self, profiles):
        rows=[]; used=[]
        for p in profiles:
            disk,sid=self._disk_from_runtime(p)
            rows.append(disk)
            if sid: used.append(sid)
        payload={"schema_version":self.SCHEMA_VERSION,"profiles":rows}
        atomic_write_json(self.path,payload,backup=True,backup_dir=self.backups)
        self.credentials.retain(used)

    @staticmethod
    def _unique_name(profiles,name,ignore_index=None):
        n=name.strip()
        if not n: raise ValueError("Tên profile không được trống")
        if any(i!=ignore_index and p.get("name","").lower()==n.lower() for i,p in enumerate(profiles)):
            raise ValueError("Tên profile đã tồn tại")
        return n

    def add(self, name, proxy="", game_path="", tag="", note="", fail_closed=True, auto_reconnect=True):
        profiles=self.load(); name=self._unique_name(profiles,name)
        profiles.append(self.normalize({
            "name":name,"proxy":proxy,"game_path":game_path,"tag":tag,"note":note,
            "fail_closed":fail_closed,"auto_reconnect":auto_reconnect
        }))
        self.save(profiles); return profiles

    def update(self, index, name, proxy="", game_path="", tag="", note="", fail_closed=True, auto_reconnect=True):
        profiles=self.load()
        if not 0 <= index < len(profiles): raise IndexError("Profile không tồn tại")
        name=self._unique_name(profiles,name,index)
        profiles[index]=self.normalize({
            "name":name,"proxy":proxy,"game_path":game_path,"tag":tag,"note":note,
            "fail_closed":fail_closed,"auto_reconnect":auto_reconnect
        })
        self.save(profiles); return profiles

    def delete(self,index):
        profiles=self.load()
        if not 0 <= index < len(profiles): raise IndexError("Profile không tồn tại")
        profiles.pop(index); self.save(profiles); return profiles

    def clone(self,index,new_name=None):
        profiles=self.load()
        if not 0 <= index < len(profiles): raise IndexError("Profile không tồn tại")
        src=dict(profiles[index]); base=(new_name or (src["name"]+" Copy")).strip()
        name=base; n=2
        existing={p.get("name","").lower() for p in profiles}
        while name.lower() in existing:
            name=f"{base} {n}"; n+=1
        src["name"]=name; profiles.append(self.normalize(src)); self.save(profiles)
        return profiles[-1]

    def merge_import(self, rows):
        profiles=self.load(); added=0; skipped=0
        existing={p.get("name","").lower() for p in profiles}
        for raw in rows:
            p=self.normalize(raw); name=p["name"].strip()
            if not name or name.lower() in existing:
                skipped+=1; continue
            p["name"]=name; profiles.append(p); existing.add(name.lower()); added+=1
        self.save(profiles); return added,skipped

    def safe_export(self):
        out=[]
        for p in self.load():
            q=dict(p)
            base,_=self._split_auth(q.get("proxy",""))
            q["proxy"]=base
            out.append(q)
        return out
