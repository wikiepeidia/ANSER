# -*- coding: utf-8 -*-
"""
eval_dataset.py — Bộ 70 câu hỏi để đo chất lượng RAG.

Mỗi câu ghi rõ điều khoản ĐÚNG, để chấm được recall thay vì đọc bằng mắt.

Năm nhóm:
    tra_cuu    20  tra cứu trực tiếp một điều khoản
    tinh_toan  15  cần con số -> phải qua mcp_server, không để LLM tự tính
    hieu_luc   10  bẫy: quy định đã bị thay hoặc chưa có hiệu lực
    ngu_canh   10  cần CẢ Điều mới trả lời đúng (khoản ngoại lệ cách xa quy tắc)
    ngoai_pham_vi 15  phải TỪ CHỐI, không được bịa

Nhóm `ngu_canh` là nhóm chứng minh việc nâng max_model_len 4096 -> 8192 có
đáng hay không. Nếu nhóm này không cải thiện so với baseline 4096, nên hạ về
4096 và lấy lại ~2 giây độ trễ mỗi câu.

Trường `dieu_dung`: danh sách (so_hieu, dieu) mà chunk trả về PHẢI chứa ít
nhất một. Để None với câu ngoài phạm vi.
"""

from __future__ import annotations

LUAT48 = "48/2024/QH15"
ND181 = "181/2025/NĐ-CP"
TT69 = "69/2025/TT-BTC"
NQ204 = "204/2025/QH15"
ND174 = "174/2025/NĐ-CP"

EVAL_SET = [
    # ---------------------------------------------------- tra cứu (20)
    dict(nhom="tra_cuu", cau="Thuế suất thuế giá trị gia tăng thông thường là bao nhiêu",
         dieu_dung=[(LUAT48, "9")]),
    dict(nhom="tra_cuu", cau="Mức thuế suất 5% áp dụng cho những hàng hóa dịch vụ nào",
         dieu_dung=[(LUAT48, "9")]),
    dict(nhom="tra_cuu", cau="Hàng hóa dịch vụ nào được áp dụng thuế suất 0%",
         dieu_dung=[(LUAT48, "9")]),
    dict(nhom="tra_cuu", cau="Đối tượng nào không chịu thuế giá trị gia tăng",
         dieu_dung=[(LUAT48, "5")]),
    dict(nhom="tra_cuu", cau="Người nộp thuế giá trị gia tăng gồm những ai",
         dieu_dung=[(LUAT48, "4")]),
    dict(nhom="tra_cuu", cau="Giá tính thuế giá trị gia tăng được xác định thế nào",
         dieu_dung=[(LUAT48, "7")]),
    dict(nhom="tra_cuu", cau="Thời điểm xác định thuế giá trị gia tăng khi bán hàng hóa",
         dieu_dung=[(LUAT48, "8"), (ND181, "8")]),
    dict(nhom="tra_cuu", cau="Phương pháp khấu trừ thuế áp dụng cho đối tượng nào",
         dieu_dung=[(LUAT48, "11")]),
    dict(nhom="tra_cuu", cau="Phương pháp tính trực tiếp trên giá trị gia tăng là gì",
         dieu_dung=[(LUAT48, "12")]),
    dict(nhom="tra_cuu", cau="Điều kiện khấu trừ thuế giá trị gia tăng đầu vào",
         dieu_dung=[(LUAT48, "14"), (ND181, "26")]),
    dict(nhom="tra_cuu", cau="Các trường hợp được hoàn thuế giá trị gia tăng",
         dieu_dung=[(LUAT48, "15")]),
    dict(nhom="tra_cuu", cau="Quy định về hóa đơn chứng từ trong thuế giá trị gia tăng",
         dieu_dung=[(LUAT48, "16")]),
    dict(nhom="tra_cuu", cau="Hóa đơn từ 5 triệu đồng trở lên cần chứng từ thanh toán nào",
         dieu_dung=[(ND181, "26")]),
    dict(nhom="tra_cuu", cau="Sản phẩm trồng trọt chưa chế biến có chịu thuế giá trị gia tăng không",
         dieu_dung=[(LUAT48, "5"), (ND181, "4")]),
    dict(nhom="tra_cuu", cau="Dịch vụ y tế có thuộc đối tượng không chịu thuế không",
         dieu_dung=[(LUAT48, "5"), (ND181, "4")]),
    dict(nhom="tra_cuu", cau="Nhà cung cấp nước ngoài không có cơ sở thường trú nộp thuế thế nào",
         dieu_dung=[(LUAT48, "4"), (TT69, "9")]),
    dict(nhom="tra_cuu", cau="Hồ sơ thủ tục áp dụng thuế suất 0% gồm những gì",
         dieu_dung=[(TT69, "4")]),
    dict(nhom="tra_cuu", cau="Hoàn thuế giá trị gia tăng đối với dự án đầu tư",
         dieu_dung=[(LUAT48, "15"), (ND181, "28")]),
    dict(nhom="tra_cuu", cau="Khấu trừ thuế đối với tài sản cố định là ô tô dưới 9 chỗ ngồi",
         dieu_dung=[(ND181, "26")]),
    dict(nhom="tra_cuu", cau="Những nhóm hàng hóa nào không được giảm thuế giá trị gia tăng",
         dieu_dung=[(NQ204, "1"), (ND174, "1")]),

    # ---------------------------------------------------- tính toán (15)
    dict(nhom="tinh_toan", cau="Bán 12 hộp trà giá 85.000 đồng mỗi hộp thì thuế giá trị gia tăng phải nộp bao nhiêu",
         dieu_dung=[(NQ204, "1"), (ND174, "1")], can_tool=True),
    dict(nhom="tinh_toan", cau="Trà thảo mộc hiện chịu thuế suất bao nhiêu phần trăm",
         dieu_dung=[(NQ204, "1"), (ND174, "1")], can_tool=True),
    dict(nhom="tinh_toan", cau="Hàng hóa thông thường sau khi giảm 2% còn thuế suất bao nhiêu",
         dieu_dung=[(NQ204, "1"), (ND174, "1")], can_tool=True),
    dict(nhom="tinh_toan", cau="Tỷ lệ phần trăm tính thuế với hoạt động phân phối cung cấp hàng hóa",
         dieu_dung=[(LUAT48, "12"), (TT69, "5")], can_tool=True),
    dict(nhom="tinh_toan", cau="Tỷ lệ tính thuế với dịch vụ xây dựng không bao thầu nguyên vật liệu",
         dieu_dung=[(LUAT48, "12"), (TT69, "5")], can_tool=True),
    dict(nhom="tinh_toan", cau="Tỷ lệ tính thuế với hoạt động sản xuất vận tải có gắn với hàng hóa",
         dieu_dung=[(LUAT48, "12"), (TT69, "5")], can_tool=True),
    dict(nhom="tinh_toan", cau="Tỷ lệ tính thuế với hoạt động kinh doanh khác là bao nhiêu",
         dieu_dung=[(LUAT48, "12"), (TT69, "5")], can_tool=True),
    dict(nhom="tinh_toan", cau="Doanh thu bao nhiêu thì hộ kinh doanh không phải nộp thuế giá trị gia tăng",
         dieu_dung=[(LUAT48, "5"), (LUAT48, "17")], can_tool=True),
    dict(nhom="tinh_toan", cau="Số thuế đầu vào chưa khấu trừ hết bao nhiêu thì được hoàn",
         dieu_dung=[(LUAT48, "15"), (ND181, "28")], can_tool=True),
    dict(nhom="tinh_toan", cau="Bán 1 tạ cao atiso giá 450.000 đồng một kg thì thuế bao nhiêu",
         dieu_dung=[(NQ204, "1"), (ND174, "1")], can_tool=True),
    dict(nhom="tinh_toan", cau="Hóa đơn 4 triệu 800 nghìn đồng có cần chuyển khoản để được khấu trừ không",
         dieu_dung=[(ND181, "26")], can_tool=True),
    dict(nhom="tinh_toan", cau="Mua hàng 6 triệu đồng trả bằng tiền mặt có được khấu trừ thuế không",
         dieu_dung=[(ND181, "26")], can_tool=True),
    dict(nhom="tinh_toan", cau="Giá bán chưa thuế 100.000 đồng thì giá đã có thuế là bao nhiêu",
         dieu_dung=[(LUAT48, "7"), (NQ204, "1")], can_tool=True),
    dict(nhom="tinh_toan", cau="Cửa hàng doanh thu 800 triệu một năm nộp thuế thế nào",
         dieu_dung=[(LUAT48, "12"), (LUAT48, "17")], can_tool=True),
    dict(nhom="tinh_toan", cau="Hàng xuất khẩu chịu thuế suất bao nhiêu",
         dieu_dung=[(LUAT48, "9")], can_tool=True),

    # ---------------------------------------------------- hiệu lực (10)
    dict(nhom="hieu_luc", cau="Nghị quyết giảm 2% thuế giá trị gia tăng áp dụng đến khi nào",
         dieu_dung=[(NQ204, "2")], ky_vong="phải nêu rõ hết hiệu lực 31/12/2026"),
    dict(nhom="hieu_luc", cau="Luật Thuế giá trị gia tăng 48/2024 có hiệu lực từ ngày nào",
         dieu_dung=[(LUAT48, "18")], ky_vong="01/7/2025"),
    dict(nhom="hieu_luc", cau="Quy định về mức doanh thu hộ kinh doanh có hiệu lực từ khi nào",
         dieu_dung=[(LUAT48, "18")], ky_vong="01/01/2026, muộn hơn phần còn lại"),
    dict(nhom="hieu_luc", cau="Chứng từ thanh toán không dùng tiền mặt với hàng mua trả chậm trả góp",
         dieu_dung=[(ND181, "26")],
         ky_vong="điểm g khoản 2 Điều 26 đã bị NĐ 144/2026 thay từ 20/6/2026"),
    dict(nhom="hieu_luc", cau="Nghị định 174/2025 về giảm thuế còn hiệu lực không",
         dieu_dung=[(ND174, "2")], ky_vong="đến hết 31/12/2026"),
    dict(nhom="hieu_luc", cau="Thông tư 69/2025 có hiệu lực từ ngày nào",
         dieu_dung=[(TT69, "10")], ky_vong="01/7/2025"),
    dict(nhom="hieu_luc", cau="Sang năm 2027 thuế suất giá trị gia tăng còn được giảm 2% không",
         dieu_dung=[(NQ204, "2"), (ND174, "2")], ky_vong="KHÔNG — đã hết hiệu lực"),
    dict(nhom="hieu_luc", cau="Luật Thuế giá trị gia tăng cũ số 13/2008 còn áp dụng không",
         dieu_dung=[(LUAT48, "18")], ky_vong="đã hết hiệu lực"),
    dict(nhom="hieu_luc", cau="Bảo hiểm có thuộc đối tượng không chịu thuế giá trị gia tăng không",
         dieu_dung=[(LUAT48, "5"), (ND181, "4")],
         ky_vong="NĐ 144/2026 bổ sung khoản 3a Điều 4 — corpus chưa có văn bản này"),
    dict(nhom="hieu_luc", cau="Nghị định 181/2025 đã bị sửa đổi bởi văn bản nào chưa",
         dieu_dung=[(ND181, "40")],
         ky_vong="NĐ 359/2025 và NĐ 144/2026 — corpus chưa có"),

    # ---------------------------------------------------- ngữ cảnh (10)
    # Câu mà khoản ngoại lệ nằm CÁCH XA quy tắc trong cùng một Điều.
    dict(nhom="ngu_canh", cau="Hàng xuất khẩu nào KHÔNG được áp dụng thuế suất 0%",
         dieu_dung=[(LUAT48, "9")],
         ky_vong="phải nêu các trường hợp loại trừ ở khoản 1, không chỉ quy tắc chung"),
    dict(nhom="ngu_canh", cau="Trường hợp nào không được khấu trừ thuế đầu vào dù có hóa đơn",
         dieu_dung=[(LUAT48, "14"), (ND181, "26")],
         ky_vong="phải nêu điều kiện chứng từ thanh toán"),
    dict(nhom="ngu_canh", cau="Cơ sở kinh doanh nào không được hoàn thuế dù đủ điều kiện khác",
         dieu_dung=[(LUAT48, "15"), (ND181, "28")],
         ky_vong="phải nêu khoản loại trừ"),
    dict(nhom="ngu_canh", cau="Sản phẩm nông nghiệp qua sơ chế có được miễn thuế không",
         dieu_dung=[(LUAT48, "5"), (ND181, "4")],
         ky_vong="phân biệt chưa chế biến / đã sơ chế thông thường"),
    dict(nhom="ngu_canh", cau="Hàng hóa vừa thuộc diện 5% vừa thuộc danh mục giảm thuế thì tính thế nào",
         dieu_dung=[(ND174, "1")],
         ky_vong="chỉ giảm với hàng đang chịu 10%, không áp cho 5%"),
    dict(nhom="ngu_canh", cau="Doanh nghiệp chế xuất mua hàng trong nước có được 0% không",
         dieu_dung=[(LUAT48, "9"), (ND181, "17")], ky_vong="điều kiện kèm theo"),
    dict(nhom="ngu_canh", cau="Điều kiện đầy đủ để được hoàn thuế hàng xuất khẩu",
         dieu_dung=[(LUAT48, "15"), (TT69, "7")],
         ky_vong="cần cả quy tắc và các trường hợp loại trừ"),
    dict(nhom="ngu_canh", cau="Khi nào cơ sở kinh doanh phải nộp thuế theo phương pháp trực tiếp",
         dieu_dung=[(LUAT48, "11"), (LUAT48, "12")],
         ky_vong="cần đọc cả hai điều mới đủ"),
    dict(nhom="ngu_canh", cau="Tài sản cố định nào bị hạn chế khấu trừ và mức hạn chế là bao nhiêu",
         dieu_dung=[(ND181, "26")], ky_vong="ô tô dưới 9 chỗ, ngưỡng 1,6 tỷ"),
    dict(nhom="ngu_canh", cau="Cửa hàng bán cả trà và rượu thì thuế suất áp dụng thế nào",
         dieu_dung=[(NQ204, "1"), (ND174, "1")],
         ky_vong="trà 8%, rượu thuộc TTĐB nên giữ 10%"),

    # ---------------------------------------------------- ngoài phạm vi (15)
    dict(nhom="ngoai_pham_vi", cau="Thủ tục ly hôn đơn phương cần giấy tờ gì", dieu_dung=None),
    dict(nhom="ngoai_pham_vi", cau="Cách nấu phở bò ngon tại nhà", dieu_dung=None),
    dict(nhom="ngoai_pham_vi", cau="Giá vàng SJC hôm nay bao nhiêu", dieu_dung=None),
    dict(nhom="ngoai_pham_vi", cau="Mức phạt vi phạm nồng độ cồn khi lái xe", dieu_dung=None),
    dict(nhom="ngoai_pham_vi", cau="Điều kiện hưởng lương hưu theo luật bảo hiểm xã hội", dieu_dung=None),
    dict(nhom="ngoai_pham_vi", cau="Thủ tục xin cấp giấy phép xây dựng nhà ở", dieu_dung=None),
    dict(nhom="ngoai_pham_vi", cau="Quy định về thời gian thử việc trong hợp đồng lao động", dieu_dung=None),
    dict(nhom="ngoai_pham_vi", cau="Thủ tục đăng ký nhãn hiệu độc quyền", dieu_dung=None),
    # Khó nhất: đúng lĩnh vực thuế nhưng KHÔNG có trong corpus (corpus chỉ có GTGT)
    dict(nhom="ngoai_pham_vi", cau="Thuế thu nhập cá nhân từ tiền lương tính thế nào", dieu_dung=None),
    dict(nhom="ngoai_pham_vi", cau="Giảm trừ gia cảnh cho người phụ thuộc là bao nhiêu", dieu_dung=None),
    dict(nhom="ngoai_pham_vi", cau="Thuế thu nhập doanh nghiệp có thuế suất bao nhiêu", dieu_dung=None),
    dict(nhom="ngoai_pham_vi", cau="Lệ phí môn bài năm nay phải nộp bao nhiêu", dieu_dung=None),
    dict(nhom="ngoai_pham_vi", cau="Thuế bảo vệ môi trường với xăng dầu là bao nhiêu", dieu_dung=None),
    dict(nhom="ngoai_pham_vi", cau="Thuế nhập khẩu ưu đãi đặc biệt theo hiệp định EVFTA", dieu_dung=None),
    dict(nhom="ngoai_pham_vi", cau="Thuế sử dụng đất phi nông nghiệp tính thế nào", dieu_dung=None),
]


def thong_ke():
    from collections import Counter
    c = Counter(x["nhom"] for x in EVAL_SET)
    return dict(c), len(EVAL_SET)


if __name__ == "__main__":
    c, n = thong_ke()
    for k, v in c.items():
        print(f"  {k:<16}{v:>3}")
    print(f"  {'TỔNG':<16}{n:>3}")
