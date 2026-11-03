# Cô Bé Phim cho Kodi

Add-on Kodi duyệt và phát phim từ Cô Bé Phim. Bản 1.3.0 hỗ trợ cấu hình tên miền từ xa qua GitHub.

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

Kodi kiểm tra file cấu hình này khi add-on chạy. Nếu GitHub tạm thời không truy cập được, add-on dùng cấu hình mặc định đã đóng gói.

## Cài đặt

Tải file ZIP trong thư mục `downloads`, sau đó vào Kodi → Tiện ích → Cài đặt từ tập tin zip.
