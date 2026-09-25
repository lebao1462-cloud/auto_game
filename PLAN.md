# Phong Thần Multi Client & Proxy Manager — PLAN

Cập nhật gần nhất: 2026-09-25

Quy ước:
- [x] Hoàn thành
- [~] Đã có bản hoạt động nhưng còn cần hoàn thiện
- [ ] Chưa làm
- [!] Rủi ro / cần xác minh thêm

## 1. Mục tiêu dự án

Xây dựng một tool Windows để:
- quản lý nhiều client Phong Thần;
- mỗi profile/account dùng một proxy riêng;
- mở/dừng từng client độc lập;
- tự nhận diện đúng tiến trình game;
- kiểm tra routing thực tế của từng client;
- giám sát tình trạng proxy và tiến trình;
- tránh fallback trực tiếp khi proxy lỗi;
- lưu cấu hình, log và trạng thái;
- đóng gói thành ứng dụng Windows dễ sử dụng.

---

## 2. Phase 0 — Nền tảng dự án

- [x] Tạo project tại `D:\code\phongthan_proxy_manager`
- [x] Tạo Python virtual environment trên ổ D
- [x] Cài PySide6
- [x] Cài requests
- [x] Cài PySocks
- [x] Tạo `run_app.bat`
- [x] Tạo các thư mục `data`, `logs`, `tools`
- [x] Ưu tiên package/model/tool trên ổ D
- [x] Xác nhận chạy app bằng Python venv

## 3. Phase 1 — Proxy Manager

- [x] Import proxy từ TXT
- [x] Hỗ trợ `IP:PORT`
- [x] Hỗ trợ `IP:PORT:USER:PASS`
- [x] Hỗ trợ URL có scheme như `http://`, `socks5://`
- [x] Chuẩn hóa proxy
- [x] Mask password trong UI
- [x] Test LIVE / DIE
- [x] Hiển thị Exit IP
- [x] Hiển thị latency
- [x] Hiển thị lỗi chi tiết
- [x] Dừng quá trình test
- [x] Export kết quả CSV
- [x] Loại proxy trùng trong input
- [x] Test thực tế SOCKS5 công cộng
- [x] Test proxy dùng worker pool concurrent
- [x] Test proxy song song/concurrent cho danh sách lớn
- [x] Sort/filter theo LIVE/DIE/latency
- [x] Auto retest proxy định kỳ
- [x] Lưu lịch sử chất lượng proxy vào `data\\proxy_history.csv`

## 4. Phase 2 — Profile Manager

- [x] Tạo profile
- [x] Sửa profile
- [x] Xóa profile
- [x] Lưu profile vào `data\profiles.json`
- [x] Gán proxy cho từng profile
- [x] Gán launcher/game path
- [x] Browse chọn executable
- [x] Phát hiện profile name trùng
- [x] Phát hiện proxy trùng
- [x] Phát hiện game path không tồn tại
- [x] Mask proxy password trong bảng
- [x] Double-click để sửa profile
- [x] Sửa đọc JSON UTF-8 BOM
- [x] Import/export profile (JSON/CSV)
- [x] Clone profile
- [x] Thêm note/tag cho profile

## 5. Phase 3 — Multi Client Manager

- [x] Xác định launcher thật là `autoupdate.exe`
- [x] Xác định client thật là `game.exe`
- [x] Mở launcher từ tool
- [x] Nhận diện `game.exe` mới
- [x] Gắn PID vào profile
- [x] Lưu mapping profile → PID vào `data\running.json`
- [x] Hiển thị RUNNING / OFFLINE
- [x] Hiển thị PID
- [x] Stop client theo PID
- [x] Chạy đồng thời 2 client
- [x] Phân biệt ACC-01 và ACC-02 bằng executable path riêng
- [x] Tạo client riêng:
  - `D:\PhongThanProfiles\ACC-01`
  - `D:\PhongThanProfiles\ACC-02`
- [x] Cleanup PID stale tự động
- [x] Tự cleanup mapping khi rename/delete profile
- [x] Tự nhận diện PID theo executable path, không cần nút "Nhận diện"
- [x] Launch All
- [x] Stop All
- [x] Restart từng client
- [x] Restart All
- [x] Theo dõi crash và cập nhật trạng thái tự động mỗi 1 giây

## 6. Phase 4 — Per-Client Proxy Routing

### 6.1 Nghiên cứu / nền tảng routing

- [x] Kiểm tra traffic thật của `game.exe`
- [x] Xác nhận game dùng TCP tới server Phong Thần
- [x] Xác nhận 2 client có kết nối độc lập
- [x] Kiểm tra Hyper-V / VirtualMachinePlatform
- [x] Bật Hyper-V
- [x] Bật VirtualMachinePlatform
- [x] Xác nhận hypervisor chạy sau reboot
- [x] Kiểm tra WinDivert
- [x] Tải WinDivert 2.2.2
- [x] Test driver WinDivert
- [x] Xác định WinDivert không phải lựa chọn đơn giản nhất cho proxy SOCKS theo PID
- [x] Cài Proxifier Standard trên ổ D
- [x] Xác nhận driver `ProxifierDrv` đang chạy

### 6.2 Tách client theo executable path

- [x] Tạo 2 thư mục game riêng
- [x] ACC-01 có `D:\PhongThanProfiles\ACC-01\game.exe`
- [x] ACC-02 có `D:\PhongThanProfiles\ACC-02\game.exe`
- [x] Gán launcher riêng cho từng profile
- [x] Tạo rule Proxifier theo full executable path
- [x] ACC-01 → Proxy A
- [x] ACC-02 → Proxy B

### 6.3 Routing thực tế

- [x] Test `netprobe.exe` trong ACC-01 → Exit IP Proxy A
- [x] Test `netprobe.exe` trong ACC-02 → Exit IP Proxy B
- [x] Xác nhận ACC-01 `game.exe` đi qua Proxifier local handler
- [x] Xác nhận Proxifier của ACC-01 kết nối tới `14.225.204.32:10800`
- [x] Xác nhận ACC-02 `game.exe` đi qua Proxifier local handler
- [x] Xác nhận Proxifier của ACC-02 kết nối tới `160.187.0.89:1080`
- [x] Xác nhận 2 client chạy đồng thời qua 2 proxy khác nhau
- [x] Tách updater khỏi proxy
- [x] `autoupdate.exe` chạy DIRECT
- [x] `fsonline.exe` chạy DIRECT
- [x] `upgameclient.exe` chạy DIRECT
- [x] Chỉ `game.exe` được route qua proxy
- [x] Tạo `proxifier_router.py`
- [x] Tự sinh `data\routing_active.ppx`
- [x] Tự load profile Proxifier
- [x] Thêm nút "Áp dụng Routing" vào UI
- [x] Thêm cột Routing vào Profiles
- [x] Trạng thái Routing dùng verify kết nối thật, không còn chỉ dựa trên Proxifier đang chạy
- [x] Trạng thái ROUTED được verify qua game PID -> Proxifier -> proxy endpoint
- [x] Hiển thị proxy endpoint thực tế đang được dùng
- [x] Hiển thị game server endpoint từ Proxifier file log
- [x] Detect routing sai/mất proxy với DIRECT / PROXY DOWN / ROUTING ERROR
- [x] Fail-closed: rule proxy không fallback DIRECT; nếu Proxifier dừng hoặc phát hiện DIRECT thì game bị dừng
- [x] Tự reconnect/relaunch khi proxy thay đổi trong Profile Manager
- [x] Đổi proxy khi game đang chạy theo quy trình an toàn: lưu config -> reload routing -> restart game/launcher
- [!] Proxy công cộng hiện chỉ dùng để test, không nên dùng cho tài khoản thật lâu dài

## 7. Phase 5 — Routing Verification & Fail-Closed

- [x] Tạo module verify routing thực tế
- [x] Xác định PID → local socket → Proxifier socket → proxy endpoint
- [x] Hiển thị trạng thái:
  - DIRECT
  - ROUTING
  - ROUTED
  - PROXY DOWN
  - ROUTING ERROR
- [x] Cảnh báo nếu profile có proxy nhưng game đang DIRECT
- [x] Chặn game kết nối trực tiếp khi profile yêu cầu proxy
- [x] Tự dừng game nếu proxy mất và fail-closed bật
- [x] Cho phép bật/tắt fail-closed theo profile
- [x] Kiểm tra reconnect sau khi proxy sống lại
- [x] Log mọi thay đổi route

## 8. Phase 6 — Monitoring

- [x] Monitor proxy LIVE/DIE nền
- [x] Monitor latency định kỳ
- [x] Monitor PID sống/chết
- [x] Monitor TCP connection của từng game
- [x] Monitor proxy endpoint thực tế
- [x] Monitor game server endpoint
- [x] Auto cleanup stale PID
- [x] Cảnh báo khi proxy đổi Exit IP
- [x] Cảnh báo khi 2 profile dùng cùng proxy
- [x] Cảnh báo khi game fallback DIRECT
- [x] Event log theo timestamp

## 9. Phase 7 — UX / Config / Logging

- [x] UI PySide6 chính hoàn thiện cho các chức năng trong plan hiện tại
- [x] Tab Proxy Manager
- [x] Tab Profiles
- [x] Nút Apply Routing
- [x] Cột Game/PID/Routing
- [x] Dashboard tổng quan
- [x] Màu trạng thái LIVE/DIE/RUNNING/ROUTED
- [x] Search profile
- [x] Filter profile
- [x] Settings page
- [x] Chọn thư mục data/log/tool
- [x] Lưu window size/position
- [x] Log file theo ngày
- [x] Rotate log
- [x] Export diagnostics
- [x] Nút "Verify All"
- [x] Nút "Launch All"
- [x] Nút "Stop All"
- [x] Confirm dialog cho thao tác nguy hiểm
- [x] Toast/status notification rõ ràng

## 10. Phase 8 — Data Safety & Recovery

- [x] Backup `profiles.json`
- [x] Backup routing config
- [x] Atomic save cho toàn bộ config
- [x] Auto recovery khi JSON lỗi
- [x] Version schema config
- [x] Migration config khi nâng phiên bản
- [x] Không lưu plaintext password nếu có proxy auth
- [x] Credential storage an toàn bằng Windows DPAPI

## 11. Phase 9 — Packaging Windows

- [x] Chọn PyInstaller
- [x] Build `.exe`
- [x] Bundle Qt dependency
- [x] Bundle routing helper/config
- [x] Kiểm tra quyền Administrator
- [x] Hiển thị yêu cầu elevation khi cần
- [x] Portable ZIP package
- [x] Test portable trong thư mục sạch, PATH không có Python
- [x] Test Windows 10 Pro 22H2 build 19045
- [!] Test Windows 11: chưa có máy Windows 11 online để kiểm thử thực tế
- [x] Versioning v1.0.0
- [x] Icon/app metadata
- [x] Release package `release\PhongThanProxyManager_v1.0.0_portable.zip`
- [x] Final frozen EXE/ZIP smoke test sau auth bridge: PASS, không cần Python trong PATH

## 12. Phase 10 — Final Test Matrix

- [x] 1 profile / 1 proxy
- [x] 2 profile / 2 proxy
- [x] 5 profile / 5 proxy
- [x] Proxy SOCKS5 không auth
- [x] Proxy SOCKS5 có auth
- [x] HTTP/HTTPS proxy
- [x] Proxy chết trước khi launch
- [x] Proxy chết khi đang chơi
- [x] Proxy đổi IP — test thực tế cùng một proxy endpoint: Exit IP đổi `104.28.205.240` → `160.187.0.89`, monitor phát hiện `EXIT_IP_CHANGED`
- [x] Game crash
- [x] Launcher crash
- [x] Proxifier crash — đã kill Proxifier thật; fail-closed dừng dummy game và Proxifier được khởi động/restore lại thành công
- [x] Reboot Windows — đã reboot vật lý; LastBootUpTime đổi từ `15:18:49` → `17:17:15`, ProxifierDrv tự Running và stale PID được cleanup
- [x] Stale PID sau reboot
- [x] Update game
- [x] Hai profile dùng nhầm cùng executable
- [x] Hai profile dùng trùng proxy
- [x] Kiểm tra không leak DIRECT khi fail-closed bật

---

## 13. Trạng thái hiện tại

Đã hoàn thành thực tế:
- Phase 0: hoàn thành
- Phase 1: hoàn thành
- Phase 2: hoàn thành
- Phase 3: hoàn thành
- Phase 4: hoàn thành
- Phase 5: hoàn thành và đã test fail-closed/reconnect
- Phase 6: hoàn thành và đã test monitoring/event log
- Phase 7: hoàn thành và đã test UI/config/logging
- Phase 8: hoàn thành và đã test backup/recovery/DPAPI
- Phase 9: build/release Windows 10 hoàn thành; còn Windows 11 physical test do chưa có máy online
- Phase 10: hoàn thành toàn bộ; 18/18 matrix PASS và 3 case môi trường trước đây đã được kiểm thử vật lý thành công

Trạng thái test gần nhất:
- 2026-09-25: Final Test Matrix 18/18 PASS
- Authenticated SOCKS5 đã test qua production auth bridge và không ghi password vào PPX
- Fail-closed đã test không fallback DIRECT khi proxy chết
- Updater vẫn DIRECT; chỉ `game.exe` và `netprobe.exe` được route
- Báo cáo chi tiết: `TEST_REPORT.md`

---

## 14. Quy tắc cập nhật PLAN

Từ thời điểm file này được tạo:
1. Mỗi khi hoàn thành một mục, đổi `[ ]` hoặc `[~]` thành `[x]`.
2. Không đánh dấu hoàn thành nếu chưa test thực tế.
3. Nếu mới có prototype nhưng chưa ổn định, dùng `[~]`.
4. Nếu phát hiện lỗi hoặc giới hạn mới, thêm mục vào đúng Phase.
5. Sau mỗi Phase lớn, cập nhật phần "Trạng thái hiện tại".
6. PLAN.md là nguồn theo dõi tiến độ chính của dự án.
