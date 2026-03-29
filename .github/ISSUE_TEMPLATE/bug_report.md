---
name: Báo lỗi (Bug Report)
about: Mô tả lỗi để nhóm có thể sửa
title: 'fix(<scope>): <mô tả ngắn>'
labels: bug
assignees: ''
---

## Mô tả lỗi
<!-- Mô tả rõ lỗi xảy ra là gì -->

## Các bước tái hiện lỗi
1. Chạy `...`
2. Truy cập trang `...`
3. Thực hiện hành động `...`
4. Thấy lỗi

## Hành vi mong đợi
<!-- Mô tả điều gì nên xảy ra -->

## Thông báo lỗi / Log
```
Dán log hoặc traceback ở đây
```

## Môi trường
- **Nhánh**: `backend` / `dev` / `main` (ghi rõ)
- **Service**: `app.py` / `dl_service` / `ai_agent_service`
- **OS**: Windows / Linux / macOS
- **Python**: (vd: 3.11)

## Screenshots
<!-- Nếu có, đính kèm ảnh chụp màn hình -->

## Quy tắc xử lý lỗi
- Commit fix theo format: `fix(<scope>): <mô tả>` (xem README)
- Fix trên nhánh `backend` hoặc `frontend`, KHÔNG fix trực tiếp trên `main`
- Tag người liên quan bằng `@username`
