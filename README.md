# Cô Bé Phim cho Kodi và Android TV

Add-on Kodi 1.3.1 và APK Android TV 1.3.0 duyệt, phát phim từ Cô Bé Phim. Cả hai hỗ trợ cấu hình tên miền từ xa qua GitHub.

## Đổi tên miền từ xa

Chỉ cần sửa `web_origin` trong [`config.json`](config.json), ví dụ:

```json
{
  "config_version": 2,
  "web_origin": "https://ten-mien-moi.example",
  "api_base": "https://api.example/api/v1",
  "embed_base": "https://api.example/embed/"
}
```

Kodi kiểm tra file cấu hình này khi add-on chạy. APK Android TV tải lại cấu hình khi có yêu cầu mới (tối đa một lần mỗi phút). Nếu GitHub tạm thời không truy cập được, cả hai dùng cấu hình mặc định đã đóng gói.

## Cài đặt

- Android TV: tải [`cobetv-1.3.0-remote.apk`](downloads/cobetv-1.3.0-remote.apk) rồi cài đè lên bản 1.0.1. Bản này giữ nguyên chữ ký và dữ liệu của app cũ.
- Kodi: tải [`plugin.video.cobephim-1.3.1.zip`](downloads/plugin.video.cobephim-1.3.1.zip), sau đó vào Kodi → Tiện ích → Cài đặt từ tập tin zip. Danh sách phim bộ được xếp từ tập 1 tăng dần.

APK giữ nguyên màn hình kích hoạt của ứng dụng gốc. Khi nguồn mặc định chỉ là trang nhúng, app tự tìm server khác của cùng tập có luồng HLS/MP4 để phát trực tiếp.
