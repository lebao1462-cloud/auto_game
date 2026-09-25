import win32gui, win32con, time, psutil
targets=[]
def enum(hwnd,_):
    try:
        _,pid=win32gui.GetWindowThreadProcessId(hwnd)
        if psutil.Process(pid).name().lower()=="proxifier.exe":
            targets.append((hwnd,pid,win32gui.GetClassName(hwnd),win32gui.GetWindowText(hwnd)))
    except: pass
win32gui.EnumWindows(enum,None)
print("TOP",targets)
for hwnd,pid,cls,title in targets:
    if cls=="#32770":
        child=win32gui.GetDlgItem(hwnd,1)
        print("BUTTON",hex(child) if child else None)
        if child:
            win32gui.SendMessage(child,win32con.BM_CLICK,0,0)
            print("SENT_BM_CLICK")
time.sleep(2)
targets=[]
win32gui.EnumWindows(enum,None)
print("AFTER",targets)
