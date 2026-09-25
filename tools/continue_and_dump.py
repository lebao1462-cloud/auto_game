from pywinauto import Application
import time
app=Application(backend="win32").connect(path=r"D:\code\phongthan_proxy_manager\tools\ProxifierStandard\Proxifier.exe")
for w in app.windows():
    if w.class_name()=="#32770":
        for c in w.children():
            if c.class_name()=="Button" and c.control_id()==1:
                c.click()
                print("CLICKED_CONTINUE")
                time.sleep(2)
                break
for w in app.windows():
    print("WINDOW",repr(w.window_text()),w.class_name())
    try:
        for c in w.children()[:40]:
            print(" ",c.class_name(),repr(c.window_text()),c.control_id())
    except: pass
