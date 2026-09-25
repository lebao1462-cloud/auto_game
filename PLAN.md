# Phong Thần One-Click Multi Account Manager — PLAN V2

Cập nhật: 2026-09-25

> PLAN V1 đã được lưu tại `PLAN_V1.md`.
> V2 giữ lại backend routing/monitoring đã test ổn, nhưng viết lại trải nghiệm sử dụng theo hướng **người dùng chỉ việc bấm Mở ACC 1, ACC 2, ...**.

Quy ước:
- [x] Hoàn thành và đã test
- [~] Có prototype nhưng chưa đạt acceptance test
- [ ] Chưa làm
- [!] Rủi ro / cần xác minh

## 1. Mục tiêu V2

Người dùng bình thường không cần biết:
- Proxifier profile là gì;
- PID/game.exe là gì;
- thư mục clone ở đâu;
- phải tạo Profile như thế nào;
- phải Apply Routing lúc nào.

Mục tiêu cuối:
1. Mở chương trình.
2. Thấy các thẻ `ACC 1`, `ACC 2`, `ACC 3`, ...
3. Bấm **Mở ACC 1**.
4. Tool tự chuẩn bị folder, proxy, routing, launcher, PID và monitoring.
5. Tool lấy username/password game đã lưu an toàn cho đúng ACC.
6. Tool tự điền username/password vào launcher và tự bấm nút đăng nhập.
7. Sau khi game mở, tool tự nhận diện `game.exe`, map PID, verify routing và chuyển trạng thái sang `ROUTED`.
8. Nếu auto-login không nhận diện được form đăng nhập hoặc đăng nhập thất bại, tool dừng tự động và chuyển sang trạng thái `CẦN ĐĂNG NHẬP THỦ CÔNG`.
## 2. Nguyên tắc UX

- Màn hình chính là **Danh sách ACC**, không phải Proxy Manager/Profile Manager.
- Các chức năng kỹ thuật chuyển vào trang **Cài đặt nâng cao**.
- Mỗi ACC có trạng thái dễ hiểu:
  - CHƯA CÀI
  - SẴN SÀNG
  - ĐANG MỞ
  - CHỜ ĐĂNG NHẬP
  - ĐÃ VÀO GAME
  - ĐANG ROUTE
  - ROUTED
  - PROXY LỖI
  - GAME LỖI
- Một nút chính duy nhất theo trạng thái:
  - `Thiết lập`
  - `Mở ACC`
  - `Dừng ACC`
  - `Mở lại`
- Không yêu cầu người dùng bấm Apply Routing thủ công.
- Không yêu cầu người dùng tự clone game folder.
- Không yêu cầu người dùng tự gán game.exe/PID.
- Không hiển thị password proxy dạng plaintext.
- Không hiển thị password game dạng plaintext sau khi đã lưu.
- Auto-login phải gắn đúng cửa sổ launcher của đúng ACC, không click theo tọa độ màn hình một cách mù.
- Ưu tiên UI Automation/pywinauto để tìm ô tài khoản, ô mật khẩu và nút đăng nhập; chỉ dùng click theo tọa độ tương đối cửa sổ như fallback đã được validate.

## 3. Luồng sử dụng chuẩn

### Lần đầu
- Chọn thư mục game gốc một lần.
- Chọn số lượng ACC muốn dùng.
- Nhập/dán danh sách proxy.
- Nhập username/password game cho từng ACC hoặc chọn bỏ qua để thêm sau.
- Bật/tắt `Tự đăng nhập` riêng cho từng ACC.
- Bấm **Thiết lập tự động**.
- Tool tự tạo ACC 1...N và lưu credential game bằng Windows DPAPI.

### Các lần sau
- Mở tool.
- Chọn ACC cần chạy.
- Bấm **Mở ACC**.
- Tool tự mở launcher đúng ACC và chuẩn bị routing.
- Nếu ACC có credential và `Tự đăng nhập` đang bật, tool tự điền username/password và tự bấm đăng nhập.
- Sau khi đăng nhập thành công, tool tự theo dõi phần còn lại cho đến khi trạng thái `ROUTED`.
- Nếu auto-login lỗi, tool không thử liên tục; chuyển sang `CẦN ĐĂNG NHẬP THỦ CÔNG` và chờ người dùng xử lý.

### Quy định về credential và auto-login game
- V2 **có lưu username/password game** khi người dùng chọn lưu.
- Username/password game phải được lưu bằng **Windows DPAPI** hoặc Windows Credential Manager; không lưu plaintext trong JSON, log, diagnostics hay Git.
- Mỗi ACC có credential riêng, tham chiếu bằng key như `game:ACC-01`.
- `accounts.json` chỉ lưu `credential_ref` và cờ `auto_login`, không chứa password thật.
- UI chỉ hiển thị password dạng mask và có nút `Đổi credential` / `Xóa credential`.
- Auto-login ưu tiên **pywinauto/UI Automation** để tìm đúng control theo cửa sổ launcher của đúng ACC.
- Nếu UI Automation không truy cập được control, cho phép fallback click/type theo tọa độ tương đối cửa sổ nhưng phải validate executable path, window title/class và kích thước cửa sổ trước khi thao tác.
- Không được click/type vào cửa sổ khác hoặc ACC khác.
- Mỗi lần bấm `Mở ACC` chỉ thực hiện tối đa một chu kỳ auto-login; không retry vô hạn để tránh khóa tài khoản khi sai mật khẩu.
- Nếu phát hiện thông báo sai tài khoản/mật khẩu hoặc launcher thay đổi UI, dừng auto-login và yêu cầu đăng nhập thủ công.
- Credential game không được đưa vào export diagnostics, clipboard, log hoặc GitHub.
## 4. Kiến trúc V2

Giữ lại các module đã ổn định:
- `proxy_core.py`
- `profile_store.py`
- `game_launcher.py`
- `proxifier_router.py`
- `routing_verify.py`
- `route_guard.py`
- `monitoring.py`
- `credential_store.py`
- `safe_io.py`

Bổ sung lớp orchestration:
- `account_store.py` — dữ liệu ACC theo slot
- `account_service.py` — setup/clone/repair/start/stop
- `account_orchestrator.py` — one-click flow
- `account_card.py` — widget UI cho từng ACC
- `setup_wizard.py` — wizard lần đầu
- `preflight.py` — kiểm tra điều kiện trước launch
- `game_credential_store.py` — lưu credential game bằng DPAPI
- `login_automation.py` — tìm đúng launcher, điền credential và bấm đăng nhập
- `login_detector.py` — nhận diện login form / login success / login error

Không xóa backend V1 cho tới khi V2 vượt toàn bộ regression test.

---

## 5. Phase V2-1 — Data Model theo ACC Slot

- [ ] Tạo model `AccountSlot`
- [ ] Mỗi slot có:
  - `slot_id` như `ACC-01`
  - tên hiển thị
  - proxy
  - thư mục game riêng
  - launcher path
  - trạng thái setup
  - fail-closed
  - auto reconnect
  - `credential_ref`
  - `auto_login`
- [ ] Tạo `data/accounts.json`
- [ ] Schema version riêng cho V2
- [ ] Migration từ `profiles.json` hiện tại sang account slots
- [ ] Không làm mất cấu hình ACC-01/ACC-02 hiện tại
- [ ] Proxy auth tiếp tục lưu bằng DPAPI
- [ ] Game username/password lưu riêng bằng DPAPI
- [ ] `accounts.json` chỉ lưu `credential_ref`, không lưu password
- [ ] Atomic save + backup
- [ ] Cho phép thêm/xóa/đổi tên slot

### Acceptance test V2-1
- [ ] Load được ACC-01 và ACC-02 cũ
- [ ] Restart app vẫn giữ đúng cấu hình
- [ ] JSON lỗi có thể recovery
- [ ] Không có password proxy plaintext trong file
- [ ] Không có username/password game plaintext trong `accounts.json`, log, diagnostics
- [ ] Credential game đọc lại đúng sau restart Windows/user session
- [ ] Test pass mới chuyển V2-2

---

## 6. Phase V2-2 — Auto Setup / Auto Clone Game

- [ ] Thêm cấu hình `Game gốc`
- [ ] Tool tự phát hiện:
  - `autoupdate.exe`
  - `game.exe`
- [ ] Người dùng chỉ chọn folder game gốc một lần
- [ ] Người dùng nhập số lượng ACC cần tạo
- [ ] Tự tạo:
  - `D:\PhongThanProfiles\ACC-01`
  - `D:\PhongThanProfiles\ACC-02`
  - ...
- [ ] Clone/copy game gốc sang từng ACC
- [ ] Có progress bar khi clone
- [ ] Không clone lại file không thay đổi nếu ACC đã tồn tại
- [ ] Có kiểm tra dung lượng ổ D trước khi clone
- [ ] Nếu clone gián đoạn, lần sau resume/repair được
- [ ] Có nút `Repair ACC`
- [ ] Không xóa save/config người dùng khi repair
- [ ] Validate mỗi ACC có launcher/game.exe riêng

### Acceptance test V2-2
- [ ] Tạo mới 2 ACC hoàn toàn tự động
- [ ] Tạo mới 5 ACC hoàn toàn tự động
- [ ] Cancel giữa chừng không làm hỏng ACC đã có
- [ ] Repair một ACC thiếu game.exe thành công
- [ ] Hai ACC không trỏ cùng executable path
- [ ] Test pass mới chuyển V2-3

---

## 7. Phase V2-3 — Auto Proxy Assignment

- [ ] Wizard có ô dán danh sách proxy
- [ ] Test proxy tự động trước khi gán
- [ ] Tự gán proxy theo thứ tự:
  - Proxy 1 → ACC 1
  - Proxy 2 → ACC 2
  - ...
- [ ] Không cho 2 ACC dùng cùng proxy nếu chế độ strict bật
- [ ] Hiển thị proxy dưới dạng mask
- [ ] Nếu thiếu proxy, ACC tương ứng báo `CHƯA CÓ PROXY`
- [ ] Cho phép đổi proxy bằng một nút trên card ACC
- [ ] Khi đổi proxy:
  - test proxy mới
  - update config
  - rebuild routing
  - restart ACC nếu đang chạy
- [ ] Có nút `Tự chọn proxy LIVE`
- [ ] Không route ACC nếu proxy DIE và fail-closed bật

### Acceptance test V2-3
- [ ] 5 proxy LIVE gán đúng cho 5 ACC
- [ ] Proxy DIE không được gán ở chế độ auto
- [ ] Proxy auth hoạt động
- [ ] Đổi proxy khi game đang chạy không leak DIRECT
- [ ] Test pass mới chuyển V2-4

---

## 8. Phase V2-4 — One-Click Open Account

Khi bấm **Mở ACC 1**, orchestration phải tự chạy:

- [ ] Kiểm tra account slot tồn tại
- [ ] Kiểm tra folder game
- [ ] Repair tự động nếu file quan trọng thiếu
- [ ] Kiểm tra proxy
- [ ] Kiểm tra Proxifier driver
- [ ] Tự Apply Routing
- [ ] Kiểm tra executable path không trùng ACC khác
- [ ] Mở `autoupdate.exe`
- [ ] Xác định đúng cửa sổ launcher theo process/executable path của ACC
- [ ] Chờ form đăng nhập sẵn sàng
- [ ] Nếu `auto_login=true` và có credential:
  - đọc credential từ DPAPI
  - focus đúng cửa sổ launcher
  - điền username
  - điền password
  - tự click nút đăng nhập
- [ ] Không ghi username/password ra log
- [ ] Không copy password qua clipboard nếu có thể tránh
- [ ] Xóa biến/password buffer khỏi scope ngay sau thao tác khi có thể
- [ ] Detect đăng nhập thành công
- [ ] Detect lỗi sai tài khoản/mật khẩu
- [ ] Detect launcher UI thay đổi/không tìm thấy control
- [ ] Nếu auto-login không thể tiếp tục, hiển thị `CẦN ĐĂNG NHẬP THỦ CÔNG`
- [ ] Tự nhận diện `game.exe`
- [ ] Tự map PID
- [ ] Tự verify routing
- [ ] Chuyển card sang `ROUTED`
- [ ] Không bắt người dùng bấm nút Nhận diện
- [ ] Không bắt người dùng bấm Apply Routing
- [ ] Không mở trùng một ACC đã chạy
- [ ] Có `Mở lại ACC`
- [ ] Có `Dừng ACC`
- [ ] Có timeout và lỗi thân thiện

### Acceptance test V2-4
- [ ] Từ app vừa mở → 1 click mở ACC-01 → tự điền đúng credential → tự click đăng nhập → game mở
- [ ] Từ app vừa mở → 1 click mở ACC-02 → tự điền đúng credential → tự click đăng nhập → game mở
- [ ] Auto-login ACC-01 không nhập nhầm credential vào launcher ACC-02
- [ ] Mở đồng thời 2 ACC vẫn login đúng từng cửa sổ
- [ ] Sai password → chỉ thử một chu kỳ rồi dừng, không retry vô hạn
- [ ] Launcher UI không khớp → fallback `CẦN ĐĂNG NHẬP THỦ CÔNG`
- [ ] ACC không lưu credential → vẫn cho đăng nhập thủ công
- [ ] Sau đăng nhập, tool tự nhận diện game và tiếp tục đến `ROUTED`
- [ ] Hai ACC cùng chạy và ROUTED qua 2 proxy khác nhau
- [ ] Proxy chết → fail-closed vẫn hoạt động
- [ ] Proxifier crash → ACC bị bảo vệ
- [ ] Test pass mới chuyển V2-5

---

## 9. Phase V2-5 — Giao diện Home dạng ACC Cards

Màn hình Home:
- [ ] Grid card `ACC 1`, `ACC 2`, ...
- [ ] Mỗi card hiển thị:
  - tên ACC
  - trạng thái game
  - trạng thái proxy
  - trạng thái routing
  - trạng thái Auto Login ON/OFF
  - trạng thái credential: ĐÃ LƯU / CHƯA LƯU
  - Exit IP
  - latency
- [ ] Nút lớn `MỞ ACC`
- [ ] Nút `DỪNG`
- [ ] Nút menu `...` cho chức năng phụ
- [ ] Màu trạng thái:
  - xanh = ROUTED
  - vàng = STARTING/WAITING
  - đỏ = ERROR/PROXY DOWN
  - xám = OFFLINE
- [ ] Không hiển thị PID ở Home
- [ ] Không hiển thị full path ở Home
- [ ] Không hiển thị cấu hình Proxifier ở Home
- [ ] Có `Mở tất cả`
- [ ] Có `Dừng tất cả`
- [ ] Có counter `Đang chạy X/N`
- [ ] Có nút `+ Thêm ACC`
- [ ] Menu `...` có:
  - Đổi tài khoản đăng nhập
  - Đổi mật khẩu
  - Bật/tắt Auto Login
  - Xóa credential đã lưu

### Acceptance test V2-5
- [ ] Người mới nhìn giao diện biết ngay nút cần bấm
- [ ] Mở từng ACC không cần vào tab khác
- [ ] Stop/Restart đúng ACC
- [ ] Home update trạng thái realtime
- [ ] Test pass mới chuyển V2-6

---

## 10. Phase V2-6 — First-Run Wizard

- [ ] Tự phát hiện chưa setup khi mở lần đầu
- [ ] Wizard Step 1: chọn game gốc
- [ ] Step 2: chọn số ACC
- [ ] Step 3: nhập username/password game cho từng ACC
- [ ] Step 4: chọn Auto Login ON/OFF cho từng ACC
- [ ] Step 5: nhập proxy
- [ ] Step 6: kiểm tra proxy
- [ ] Step 7: chọn nơi lưu ACC
- [ ] Step 8: Preview (password chỉ hiển thị dạng mask)
- [ ] Step 9: `Thiết lập tự động`
- [ ] Hiển thị tiến độ clone/config/routing
- [ ] Khi xong tự chuyển Home
- [ ] Có thể bỏ qua proxy và thêm sau
- [ ] Có thể chạy lại wizard từ Settings

### Acceptance test V2-6
- [ ] Xóa config V2 → mở app → wizard xuất hiện
- [ ] Setup 2 ACC từ đầu thành công, lưu đúng 2 bộ credential
- [ ] Setup 5 ACC từ đầu thành công, lưu đúng 5 bộ credential
- [ ] Password không xuất hiện plaintext trong accounts/config/log/diagnostics
- [ ] Sau restart app vẫn auto-login đúng từng ACC
- [ ] Không cần mở Proxy Manager/Profile Manager
- [ ] Test pass mới chuyển V2-7

---

## 11. Phase V2-7 — Advanced Mode

Các phần kỹ thuật cũ không xóa mà chuyển vào:
- [ ] `Settings > Advanced`
- [ ] Proxy Manager
- [ ] Profile/Account raw config
- [ ] Routing diagnostics
- [ ] PID/socket details
- [ ] Log viewer
- [ ] Export diagnostics
- [ ] Credential manager cho game account
- [ ] Nút xem trạng thái credential nhưng không hiển thị password thật
- [ ] Nút xóa/đổi credential từng ACC

Mặc định:
- [ ] Advanced Mode đóng
- [ ] Người dùng phổ thông không thấy các chi tiết kỹ thuật

### Acceptance test V2-7
- [ ] Home vẫn hoạt động khi Advanced Mode đóng
- [ ] Có thể debug đầy đủ khi bật Advanced Mode
- [ ] Test pass mới chuyển V2-8
---

## 12. Phase V2-8 — Reliability / Final Release

- [ ] Preflight trước mọi launch
- [ ] Startup recovery sau Windows reboot
- [ ] Recovery khi app crash
- [ ] Recovery khi Proxifier crash
- [ ] Auto cleanup stale PID
- [ ] Detect ACC folder bị đổi/xóa
- [ ] Detect game update làm thay đổi executable
- [ ] Repair routing tự động
- [ ] Không bao giờ fallback DIRECT khi fail-closed bật
- [ ] Background monitor không block UI
- [ ] Clone/copy không block UI
- [ ] Log orchestration theo từng ACC
- [ ] Export diagnostics theo ACC

### Final Matrix V2
- [ ] First-run setup 1 ACC
- [ ] First-run setup 2 ACC
- [ ] First-run setup 5 ACC
- [ ] Secure credential store 1 ACC
- [ ] Secure credential store 5 ACC
- [ ] Auto-login ACC 1
- [ ] Auto-login ACC 2
- [ ] Auto-login đồng thời nhiều ACC không nhập nhầm credential
- [ ] Auto-login sai password dừng an toàn
- [ ] Auto-login khi launcher UI thay đổi fallback manual
- [ ] Xóa credential → ACC không còn auto-login
- [ ] Restart Windows → credential DPAPI vẫn đọc đúng với cùng Windows user
- [ ] One-click ACC 1
- [ ] One-click ACC 2
- [ ] Open All
- [ ] Stop All
- [ ] Restart 1 ACC
- [ ] Proxy chết trước launch
- [ ] Proxy chết khi game chạy
- [ ] Đổi proxy khi game chạy
- [ ] Game crash
- [ ] Launcher crash
- [ ] Proxifier crash
- [ ] Windows reboot
- [ ] Folder ACC thiếu file
- [ ] Hai ACC trùng executable
- [ ] Hai ACC trùng proxy
- [ ] SOCKS5 auth
- [ ] SOCKS5 no-auth
- [ ] HTTP proxy
- [ ] Không leak DIRECT

Release:
- [ ] Version `v2.0.0`
- [ ] Build portable EXE
- [ ] Test máy sạch
- [ ] Update README
- [ ] Update TEST_REPORT
- [ ] Upload GitHub

---

## 13. Definition of Done

### Yêu cầu đăng nhập tài khoản game của V2
- **Auto-login là chức năng chính của V2.**
- One-click trong V2 có nghĩa là: **một click để chuẩn bị đúng ACC, mở launcher, tự điền username/password, tự bấm đăng nhập và tiếp tục giám sát tới ROUTED**.
- Username/password game được phép lưu nhưng phải lưu bằng Windows DPAPI/Windows Credential Manager, không plaintext.
- `accounts.json` / `profiles.json` chỉ được lưu tham chiếu credential và cờ `auto_login`.
- Credential game tuyệt đối không xuất hiện trong log, diagnostics, export profile, clipboard history hoặc GitHub.
- Auto-login phải xác thực đúng process/executable/window của từng ACC trước khi type/click.
- Không được dùng global screen coordinate click nếu chưa validate đúng cửa sổ.
- Sai credential hoặc UI launcher không khớp phải dừng tự động và chuyển sang đăng nhập thủ công; không retry vô hạn.
- Người dùng phải có nút đổi/xóa credential và bật/tắt Auto Login cho từng ACC.

Một Phase chỉ được đổi sang `[x]` khi:
1. Code đã triển khai.
2. Compile/pass static check.
3. Có test tự động nếu phù hợp.
4. Có smoke test UI/thực tế.
5. Không phá chức năng V1 đang dùng.
6. Cập nhật PLAN ngay sau khi test PASS.

Không chuyển Phase tiếp theo nếu Phase hiện tại còn lỗi blocker.
## 14. Mục tiêu giao diện cuối

Ví dụ Home mong muốn:

```text
┌──────────────────────────────────────────────┐
│  Phong Thần Multi Account Manager            │
│  Đang chạy: 2 / 5         Proxy LIVE: 5 / 5 │
├──────────────────────────────────────────────┤
│ ACC 1   ● ROUTED                             │
│ Proxy: LIVE  86ms      Exit IP: xxx.xxx.xxx │
│                [ DỪNG ACC ]                  │
├──────────────────────────────────────────────┤
│ ACC 2   ○ OFFLINE                            │
│ Proxy: LIVE  102ms                           │
│                [ MỞ ACC ]                    │
├──────────────────────────────────────────────┤
│ ACC 3   ○ OFFLINE                            │
│ Proxy: LIVE  76ms                            │
│                [ MỞ ACC ]                    │
└──────────────────────────────────────────────┘

[ + Thêm ACC ]    [ Mở tất cả ]    [ Dừng tất cả ]
```

Người dùng không cần biết profile, PID, Proxifier rule hay thư mục clone để sử dụng bình thường.

## 15. Việc bắt đầu tiếp theo

Bắt đầu từ **Phase V2-1 — Data Model theo ACC Slot**.

Ưu tiên xuyên suốt:
**One-click + Auto-login > bảo mật credential > tự động hóa > an toàn routing > giao diện dễ hiểu > advanced/debug cuối cùng.**
