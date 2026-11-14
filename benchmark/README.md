# Benchmark cho Emma

Dùng 15 câu dev (Q01–Q15) từ tập I–II và 5 câu test (Q16–Q20) từ tập III. Các cảnh và chương đích của hai split tách biệt. Nhân vật và cốt truyện xuất hiện xuyên tập, vì vậy đây vẫn là đánh giá trong cùng một corpus. Cả ba cấu hình tìm trên toàn bộ 55 chương. Sáu câu có phạm vi tập sách do người đọc chọn trước khi đặt câu hỏi (ba dev, ba test). Mỗi câu dùng câu hỏi tiếng Anh để phù hợp với corpus và embedding model.

Chốt trước khi chạy: ưu tiên Evidence Hit@3 trên dev, rồi Hit@1 trên dev, rồi chọn theo thứ tự A, B, C nếu hòa để ưu tiên baseline đơn giản hơn. Cố định tham số, tập câu hỏi, các vị trí audit và tiêu chí chọn trước khi chạy. Chạy toàn bộ test sau bước chọn và báo cả ba cấu hình. Đoạn trích gold được kiểm tra khớp trên văn bản đã chuẩn hóa. Công thức tự động dùng khớp nguyên văn sau gộp khoảng trắng và đúng nguồn, đúng chương. Nếu phát hiện bằng chứng tương đương ở chương khác, người rà soát cần xác minh và ghi riêng.
