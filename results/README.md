# Kiểm tra kết quả

- `summary.json` chứa số liệu máy đo theo cấu hình và split. `traces.json` chứa câu hỏi, gold, điểm cosine, metadata và văn bản top-3. `run.log` ghi các bước pipeline.
- `audit-review.json` chứa mẫu và nhận xét sơ bộ ở các trường mang tên `ai_*`. Các trường `label`, `manual_valid` và `reason` dành cho đánh giá của học viên. `matched_snapshot` là phép kiểm tra bằng code.
- Coherence: đọc 10 vị trí giống nhau mỗi cấu hình. Chấm 0 nếu ý bị cắt đến mức khó hiểu, 1 nếu hiểu một phần, 2 nếu ý được giữ đủ. B và C dùng cùng chunk, nên cùng nhãn tại mỗi vị trí.
- Metadata: mỗi dòng chỉ một kết quả test. Dùng tập/chương trong manifest để đối chiếu nguồn, trang và khoảng ký tự trên văn bản đã chuẩn hóa.
- Grounding: tìm `id` và `strategy` trong traces, đọc cả ba đoạn. Chấm 0 nếu thiếu bằng chứng, 1 nếu bằng chứng chưa đủ, 2 nếu đủ để trả lời và truy nguồn. Có thể dùng nhiều đoạn khi chấm grounding; Evidence Hit@3 chính yêu cầu một đoạn chứa đủ đoạn trích gold.
- Điền bảng audit trong báo cáo cá nhân sau khi đọc các mẫu và ghi lý do.
