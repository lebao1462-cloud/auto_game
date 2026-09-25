from pywinauto import Application
app=Application(backend="win32").connect(path=r"D:\code\phongthan_proxy_manager\tools\ProxifierStandard\Proxifier.exe")
for w in app.windows():
    print("WINDOW",repr(w.window_text()), w.class_name())
    try:
        for c in w.children():
            print(" ",c.class_name(),repr(c.window_text()),c.control_id())
    except Exception as e: print(e)
