# Chính sách bảo mật

Cảm ơn bạn đã dành thời gian giúp giữ an toàn cho **ANSER** (*Automated Nimble
Software Easing Relaxation*) và người dùng của dự án. ANSER là một nền tảng tự
động hóa bán lẻ tích hợp AI/ML được xây dựng trên Flask, gồm xử lý hóa đơn
bằng OCR, dự báo bằng mô hình LSTM, trợ lý trò chuyện AI, công cụ workflow
kéo-thả, và các tích hợp với dịch vụ Google cùng webhook Make.com. Trang này
giải thích cách báo cáo một vấn đề bảo mật và những gì bạn có thể mong đợi
từ nhóm phát triển.

---

## Phiên bản được hỗ trợ

ANSER là một dự án học thuật và phát triển nhóm đang được duy trì tích cực.
Chúng tôi chỉ phát hành bản vá bảo mật cho **nhánh phát triển hiện tại** và
**tag phát hành gần nhất**. Các snapshot cũ hơn sẽ không được vá.

| Nhánh / Tag               | Được hỗ trợ         |
| ------------------------- | ------------------- |
| `main`                    | :white_check_mark:  |
| Bản phát hành mới nhất    | :white_check_mark:  |
| Các bản phát hành cũ      | :x:                 |
| Nhánh tính năng           | :x:                 |

Nếu bạn đang chạy ANSER từ một bản clone cũ hơn quá một phiên bản nhỏ so với
`main`, hãy nâng cấp trước khi gửi báo cáo, hoặc ghi rõ mã commit trong báo
cáo của bạn.

---

## Báo cáo lỗ hổng bảo mật

**Vui lòng không mở issue công khai trên GitHub cho các vấn đề bảo mật.**
Issue công khai cho phép kẻ tấn công phát hiện lỗi trước khi người dùng kịp
vá.

### Kênh ưu tiên: báo cáo lỗ hổng riêng của GitHub

1. Vào tab **Security** của kho chứa này.
2. Nhấn **"Report a vulnerability"** để mở một bản nháp advisory riêng tư,
   chỉ những người bảo trì mới thấy được.
3. Đính kèm tất cả các mục được liệt kê trong *Những thông tin cần kèm theo*
   bên dưới.

### Kênh dự phòng: email

Nếu bạn không thể dùng luồng GitHub Security Advisories, hãy gửi email cho
nhóm bảo trì theo địa chỉ trong [`MAINTAINERS.md`](./MAINTAINERS.md) (hoặc,
nếu file đó chưa tồn tại, địa chỉ trong lịch sử commit của kho chứa). Mã hóa
các thông tin nhạy cảm bằng khóa PGP của chúng tôi nếu file đó có công khai
khóa PGP.

### Những thông tin cần kèm theo

Một báo cáo tốt sẽ tiết kiệm thời gian cho tất cả mọi người. Vui lòng đính
kèm càng nhiều mục sau đây càng tốt:

- **Tiêu đề** rõ ràng và **tóm tắt ngắn** về vấn đề.
- **Thành phần bị ảnh hưởng** (route, service, file) và commit/tag mà bạn
  tái hiện được lỗi.
- **Các bước tái hiện**, bao gồm cấu hình hoặc dữ liệu mẫu cần thiết.
- **Tác động** bạn quan sát được, và tác động xấu nhất mà bạn nghi ngờ.
- Lỗ hổng có làm lộ **dữ liệu của người dùng khác**, các bí mật của dự án,
  hay chỉ dữ liệu của chính bạn.
- Ảnh chụp màn hình, payload, hoặc log đã được làm sạch (hãy che token, mật
  khẩu, và OAuth refresh token trước khi đính kèm).

### Bạn có thể mong đợi điều gì

Chúng tôi là một nhóm nhỏ gồm sinh viên và cộng tác viên, nên thời gian phản
hồi là tối đa theo khả năng:

| Giai đoạn                                    | Thời gian mục tiêu         |
| -------------------------------------------- | -------------------------- |
| Phản hồi lần đầu                             | trong vòng 5 ngày làm việc  |
| Phân loại và đánh giá mức độ nghiêm trọng    | trong vòng 10 ngày làm việc |
| Vá cho lỗ hổng nghiêm trọng                  | sớm nhất có thể; chúng tôi sẽ thống nhất ngày công bố với bạn |
| Vá cho lỗ hổng cao / trung bình              | trong vòng 30 ngày sau phân loại |
| Công bố công khai                            | sau khi bản vá được phát hành, hoặc 90 ngày sau khi phản hồi, tùy điều kiện nào đến trước |

Nếu chúng tôi không tái hiện được vấn đề, chúng tôi sẽ hỏi thêm trước khi
quyết định đóng báo cáo.

---

## Mục tiêu trong phạm vi

Các khu vực sau đây nằm trong ranh giới bảo mật của ANSER và thuộc phạm vi
của các báo cáo:

- Ứng dụng web Flask (`app.py`, `wsgi.py`, `routes/`, `core/`,
  `templates/`, `static/`).
- Dịch vụ deep-learning OCR / dự báo (`dl_service/`, `run_dl_service.py`).
- Dịch vụ AI agent (`ai_agent_service/`, `worker.py`).
- Các đường truy cập cơ sở dữ liệu qua `core/database.py` và `database/`.
- Bộ máy workflow tự động hóa (`core/automation_engine.py`,
  `core/workflow_engine.py`).
- Tích hợp webhook và HTTP (`core/make_integration.py`,
  `core/google_integration.py`).
- Xử lý upload tệp, đặc biệt là pipeline OCR hóa đơn.
- Xác thực, phiên đăng nhập, và cách xử lý `SECRET_KEY`.
- Tải cấu hình và phân tích `.env` (`core/config.py`).

## Mục tiêu ngoài phạm vi

Các mục sau đây **không** thuộc chính sách này:

- Lỗ hổng trong **các gói bên thứ ba** mà ANSER phụ thuộc. Vui lòng báo cáo
  lên kho gốc (PyPI, GitHub) và mở issue thường ở đây để chúng tôi nâng cấp
  phiên bản.
- Vấn đề yêu cầu người dùng **đã có quyền truy cập shell**, biết
  `SECRET_KEY`, hoặc các thông tin xác thực production khác.
- **Kỹ thuật xã hội** (social engineering) nhắm vào người bảo trì hoặc cộng
  tác viên.
- Tấn công **thể tích / từ chối dịch vụ** vào các bản demo.
- **Self-XSS** không ảnh hưởng đến người dùng khác.
- Báo cáo về **nhánh cũ hoặc fork** chưa được merge vào `main`.

---

## Ghi chú cứng cáp hóa cho người vận hành

Nếu bạn chạy ANSER trong môi trường production, vui lòng xem lại những điểm
sau trước khi đưa vào vận hành. Đây là các nguồn sự cố phổ biến nhất mà
chúng tôi đã gặp:

- **Không bao giờ commit bất cứ thứ gì trong `secrets/`**. Thư mục này chứa
  các file JSON service-account của Google, OAuth token, và dump cơ sở dữ
  liệu. Hãy xoay vòng bất kỳ thông tin xác thực nào đã từng xuất hiện trong
  một commit công khai.
- **Đặt `SECRET_KEY` thành một giá trị mới, có độ ngẫu nhiên cao** thông qua
  biến môi trường. Giá trị mặc định trong `core/config.py` cố tình là một
  placeholder mà ứng dụng sẽ từ chối khởi động ở chế độ production.
- **Đặt `POSTGRES_URL`, `REDIS_URL`, và thông tin xác thực Make.com / Google
  OAuth thông qua biến môi trường hoặc trình quản lý bí mật**, không lưu
  trong mã nguồn.
- **Giới hạn endpoint upload OCR** (kích thước, MIME type, tần suất) — các
  tệp tải lên sẽ được xử lý bởi dịch vụ ML và có thể là vector cho SSRF hoặc
  cạn kiệt tài nguyên.
- **Chạy `dl_service/` và `ai_agent_service/` như các tiến trình riêng
  biệt** với quyền mạng hẹp nhất có thể; không để chúng lộ ra internet công
  cộng.

---

## Ghi nhận đóng góp

Chúng tôi rất vui khi được ghi nhận người báo cáo trong ghi chú phát hành
(với sự cho phép của bạn). Nếu bạn muốn giữ ẩn danh, hãy nói rõ trong báo
cáo.

Cảm ơn bạn đã giúp ANSER an toàn hơn cho tất cả những người dựa vào dự án.
