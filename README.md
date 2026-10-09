# Vocal Reminder Poke Version

Ứng dụng Windows học từ vựng tiếng Anh bằng quả cầu nổi và thẻ ôn tập pixel art.

## Đã có trong bản đầu

- Tạo nhiều quả cầu, đặt tên, chọn loại Poké Ball và Pokémon đi cùng. Mỗi quả cầu giữ một bộ từ riêng.
- Bấm quả cầu nổi trên màn hình để lưu từ, loại từ, nghĩa tiếng Anh, nghĩa tiếng Việt và ví dụ. Có thể kéo quả cầu đến vị trí khác.
- Ôn `m` từ sau mỗi `k` giờ hoặc bấm **Ôn ngay**. Thẻ lần lượt cho xem từ, lật nghĩa, rồi sang từ sau. Bộ chọn trộn thứ tự và duyệt hết các từ trước khi bắt đầu vòng mới.
- Dashboard hiển thị số từ đã lưu, số từ đã từng ôn, tổng lượt ôn và lượt ôn hôm nay.
- Nhắc uống nước và đi lại mỗi 30 phút qua thông báo Windows.
- Thiết lập lần đầu và tùy chọn chạy cùng Windows khi đăng nhập. Đóng cửa sổ chính sẽ thu về system tray; **Thoát** trong menu tray mới kết thúc ứng dụng.
- Dữ liệu nằm trong `%LOCALAPPDATA%\VocalReminderPoke\vocabulary.sqlite3`.

## Chạy từ mã nguồn

Yêu cầu Windows 10/11 và Python 3.12 trở lên.

```powershell
python -m venv C:\vrp-venv
C:\vrp-venv\Scripts\python.exe -m pip install -r requirements.txt
C:\vrp-venv\Scripts\python.exe main.py
```

## Tạo file EXE

```powershell
./build.ps1
```

File nhận được ở `dist/VocalReminderPoke.exe`. Mở file một lần để thiết lập bộ từ, chu kỳ nhắc và chạy cùng Windows. Sau khi chuyển EXE sang vị trí khác, hãy mở lại ở vị trí mới và lưu lại tùy chọn **Chạy cùng Windows** để cập nhật đường dẫn khởi động.

## Kế hoạch hoàn thiện

| Giai đoạn | Công việc | Trạng thái |
| --- | --- | --- |
| 1 — Nền tảng | Bộ từ, lưu từ, SQLite, quả cầu nổi, setup, system tray | Hoàn thành |
| 2 — Vòng học | Bộ chọn vét hết từ, flashcard, nhắc giờ, dashboard | Hoàn thành |
| 3 — Trải nghiệm | Hoạt ảnh quả cầu mở/đóng, âm thanh, nhiều linh vật, tương tác phản hồi đúng/sai | Tiếp theo |
| 4 — Học thông minh | Lặp lại ngắt quãng theo độ nhớ, thống kê theo ngày, tìm kiếm/sửa từ, import/export CSV | Tiếp theo |
| 5 — Phát hành | Bộ cài đặt, cập nhật phiên bản, ký số Windows, kiểm thử trên nhiều độ phân giải | Tiếp theo |

## Thiết kế và tài nguyên

Tông màu xanh navy, san hô và vàng ấm; viền đậm, chữ monospace, hình được phóng bằng nearest-neighbor để giữ điểm ảnh rõ. `assets/` chứa sáu biểu tượng Poké Ball và sáu sprite Pokémon thật từ [kho sprite PokéAPI](https://github.com/PokeAPI/sprites). `tools/download_pokemon_assets.py` ghi lại URL nguồn và có thể tải lại toàn bộ ảnh. Hai ảnh trong `asserts/pet/` chỉ là tư liệu tham khảo, không được đóng gói vào ứng dụng.

Theo [thông tin giấy phép của kho sprite](https://github.com/PokeAPI/sprites/blob/master/LICENCE.txt), bản quyền hình ảnh Pokémon thuộc The Pokémon Company. Nếu phát hành ứng dụng công khai, cần xử lý quyền sử dụng các hình này trước.

Pokémon đã chọn hiện trong cửa sổ ôn tập và quả cầu hiện lại sau thẻ cuối. Hoạt ảnh bật ra/chui vào quả cầu là phần việc tiếp theo của giai đoạn 3.
