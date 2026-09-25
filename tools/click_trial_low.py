import ctypes, subprocess, time, os
from ctypes import wintypes
exe=r"D:\code\phongthan_proxy_manager\tools\ProxifierStandard\Proxifier.exe"
subprocess.run(["taskkill","/IM","Proxifier.exe","/F"],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
p=subprocess.Popen([exe],cwd=os.path.dirname(exe))
print("PID",p.pid)
time.sleep(2)
u=ctypes.windll.user32
EnumProc=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
tops=[]
@EnumProc
def cb(h,l):
    pid=wintypes.DWORD()
    u.GetWindowThreadProcessId(h,ctypes.byref(pid))
    if pid.value==p.pid:
        tops.append(h)
    return True
u.EnumWindows(cb,0)
for h in tops:
    b=ctypes.create_unicode_buffer(256);u.GetClassNameW(h,b,256)
    t=ctypes.create_unicode_buffer(512);u.GetWindowTextW(h,t,512)
    print("TOP",hex(h),b.value,repr(t.value))
    child=u.GetDlgItem(h,1)
    if child:
        print("POST BUTTON",hex(child))
        u.PostMessageW(child,0x00F5,0,0)
time.sleep(3)
print("POLL",p.poll())
