import ctypes
from ctypes import wintypes
u=ctypes.windll.user32
EnumWindowsProc=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
EnumChildProc=ctypes.WINFUNCTYPE(wintypes.BOOL,wintypes.HWND,wintypes.LPARAM)
def text(h):
    n=u.GetWindowTextLengthW(h)
    b=ctypes.create_unicode_buffer(n+1)
    u.GetWindowTextW(h,b,n+1)
    return b.value
def cls(h):
    b=ctypes.create_unicode_buffer(256)
    u.GetClassNameW(h,b,256)
    return b.value
targets=[]
@EnumWindowsProc
def ew(h,l):
    pid=wintypes.DWORD()
    u.GetWindowThreadProcessId(h,ctypes.byref(pid))
    try:
        import psutil
        name=psutil.Process(pid.value).name()
    except Exception:
        name=''
    t=text(h)
    if 'Proxifier' in t or name.lower()=='proxifier.exe':
        print('TOP',hex(h),pid.value,repr(t),cls(h))
        @EnumChildProc
        def ec(ch,ll):
            tt=text(ch)
            cc=cls(ch)
            if tt or cc in ('Button','Edit','Static'):
                print(' CHILD',hex(ch),repr(tt),cc)
            return True
        u.EnumChildWindows(h,ec,0)
    return True
u.EnumWindows(ew,0)
