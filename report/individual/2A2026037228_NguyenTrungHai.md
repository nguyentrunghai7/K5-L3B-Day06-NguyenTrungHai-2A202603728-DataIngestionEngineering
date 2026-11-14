# Báo cáo cá nhân — Day 06

**Học viên:** Nguyễn Trung Hải · **MSSV:** 2A2026037228 · **Lớp:** L3B

## Dữ liệu và pipeline

Corpus gồm 55 chương trên ba tập *Emma* của Jane Austen, 878.458 ký tự sau chuẩn hóa. Mỗi chương là một đơn vị nguồn độc lập, dài ít nhất 1.500 ký tự. Manifest ghi ID, SHA-256, quy tắc đếm, phạm vi dòng và độ dài. Project Gutenberg ghi tác phẩm thuộc phạm vi công cộng tại Hoa Kỳ. Nguồn gốc có thông báo Project Gutenberg License. [Trang nguồn](https://www.gutenberg.org/ebooks/158) · [Manifest](../../data/manifest.json)

Python 3.11 đọc bản TXT UTF-8, chuẩn hóa Unicode NFC, gộp xuống dòng trong đoạn, giữ ranh giới đoạn và chương. Bỏ mục lục, tiêu đề và thông báo Gutenberg. Khi sai snapshot, thiếu bằng chứng hoặc backend lỗi, chương trình ghi lỗi và dừng. Metadata gồm ID tài liệu, URL, ID chương, tập, số chương trong tập và offset trên nội dung đã chuẩn hóa.

FastEmbed 0.9.1 chạy BAAI/bge-small-en-v1.5, bản ONNX lượng tử hóa của Qdrant tại revision aa8f8b060edb00e03bfdd08813a2949946c8ba55, 384 chiều. Cả truy vấn và đoạn dùng cơ chế mặc định của model trong FastEmbed. Chroma 1.5.9 lưu trên đĩa, dùng HNSW cosine. Chi phí API là 0 USD. Các thời gian đo loại thời gian tải và khởi tạo model. [Lệnh chạy](../../README.md)

## Cấu hình và benchmark

- **A** dùng chunk 500 ký tự, overlap 50 ký tự.
- **B** ghép đoạn liền nhau trong giới hạn 500 ký tự. Đoạn dài được tách ưu tiên tại hết câu, rồi ở khoảng trắng.
- **C** truy xuất trên cùng index B và áp dụng điều kiện tập sách khi người đọc đã chọn phạm vi. Ba giá trị I, II, III đến từ heading nguồn.

Benchmark có 15 câu dev từ tập I–II và 5 câu test từ tập III. Có 3 câu dev và 3 câu test dùng filter. Cả ba cấu hình tìm trên toàn bộ corpus. Tiêu chí chọn trên dev theo thứ tự Evidence Hit@3, Hit@1 và ưu tiên A, B, C khi hai chỉ số hòa. Gold được xác minh trên văn bản chuẩn hóa trước khi truy xuất. [Thiết kế benchmark](../../benchmark/README.md)

## Kết quả đo

| Cấu hình | Split | Hit@1 | Evidence Hit@3 | Top-3 đúng phạm vi | Chunk | Ingest | Chi phí API |
|---|---|---:|---:|---:|---:|---:|---:|
| A | dev | 8/15 | 9/15 | 0/3 | 1971 | 140.12 s | 0 USD |
| A | test | 1/5 | 1/5 | 1/3 | 1971 | 140.12 s | 0 USD |
| B | dev | 4/15 | 6/15 | 0/3 | 2300 | 137.57 s | 0 USD |
| B | test | 2/5 | 2/5 | 0/3 | 2300 | 137.57 s | 0 USD |
| C | dev | 4/15 | 6/15 | 3/3 | 2300 | 0 s thêm, dùng B | 0 USD |
| C | test | 2/5 | 2/5 | 3/3 | 2300 | 0 s thêm, dùng B | 0 USD |

A có 974.258 ký tự (độ dài trung vị 500, khoảng 131–500). B/C có 874.860 ký tự (trung vị 406, khoảng 23–500). Lần chạy thứ hai mở lại hai collection trên đĩa, giữ nguyên số chunk và đúng thứ tự ID top-3 ở cả 60 lượt. [Số liệu](../../results/summary.json) · [Log](../../results/run.log)

## Kiểm tra thủ công

Các vị trí coherence được chọn trước khi chạy từ ký tự giữa của 10 chương đầu, dùng cùng vị trí cho mọi cấu hình. Audit grounding và metadata dùng cả 5 câu test cho mỗi cấu hình. Chroma trả về cùng chunk cho B và C tại mỗi vị trí coherence vì dùng chung index. Coherence và grounding trong bảng là đánh giá của Codex dựa trên nội dung mẫu. Cột metadata ghi kết quả đối chiếu tự động với snapshot nguồn. Audit lưu các nhãn AI trong trường ai_* và các trường xác nhận của học viên vẫn để trống. [Mẫu audit](../../results/audit-review.json) · [Trace](../../results/traces.json)

| Cấu hình | Coherence do AI chấm /2 (10 vị trí) | Metadata khớp snapshot (tự động) | Grounding do AI chấm, số câu mức 0/1/2 và điểm trung bình |
|---|---|---|---|
| A | 1,3/2 | 15/15 | 3/1/1 · 0,6/2 |
| B | 1,5/2 | 15/15 | 2/1/2 · 1,0/2 |
| C | 1,5/2 | 15/15 | 2/1/2 · 1,0/2 |

Trường tập hữu ích khi người đọc muốn giới hạn cảnh hoặc thời kỳ trong truyện. Khi người đọc chọn nhầm tập, bộ lọc có thể loại bằng chứng đúng. Mã chương giúp truy nguồn nhưng cần đọc cùng tập vì số chương lặp lại ở mỗi tập.

## Phân tích và kết luận

**A–B.** B có nhiều chunk hơn A (2.300 so với 1.971) nhưng đưa ít ký tự vào embedding hơn vì không chồng lấn. A đạt Hit@3 dev 9/15 so với 6/15 của B. B đạt 2/5 bên test so với 1/5 của A. Chọn A theo tiêu chí đã chốt trên dev. Chênh lệch test tương ứng một câu và cần thêm mẫu để đánh giá độ ổn định.

**B–C.** Filter tăng tuân thủ phạm vi từ 0/3 lên 3/3 ở cả hai split, giữ nguyên Hit@1 và Hit@3. C dùng lại vector của B. Trong corpus này, phạm vi tập hạn chế kết quả lạc tập nhưng nhiều cảnh có chung nhân vật vẫn cạnh tranh trong cùng tập.

- **Q16, nguồn pg158 đơn vị 43 (tập III, chương VII).** A đưa ba đoạn ở đơn vị 25, 34 và 44; các đoạn kể về những buổi gặp và không nêu Box Hill. B/C xếp đoạn mở đầu chứa Box Hill ở vị trí đầu.
- **Q18, nguồn pg158 đơn vị 51 (tập III, chương XV).** B trả về các đoạn về thân thế của Jane ở đơn vị 20–21. C đưa toàn bộ kết quả vào tập III nhưng chỉ tìm được các đoạn ở 47, 54 và 45. Cả hai thiếu đoạn nêu Mrs. Smallridge.

## Giới hạn và sử dụng AI

Test chỉ có 5 câu nên một câu làm thay đổi 20 điểm phần trăm. Câu Q16 dùng mô tả chuyến đi khá rộng nên dễ khớp với những buổi gặp khác. Nên bổ sung chi tiết phân biệt khi thiết kế một bộ câu hỏi mới. Ba tập dùng chung nhân vật và cốt truyện, vì vậy kết quả chỉ phản ánh truy xuất trong corpus này. So khớp nguyên văn có thể bỏ qua bằng chứng diễn đạt tương đương. Nếu ngữ cảnh hữu ích nằm ở nhiều chunk, groundedness thủ công có thể cao hơn tỷ lệ khớp nguyên văn. Có thể mở rộng bằng nhiều cảnh khó, câu diễn đạt lại và gold thay thế được xác minh trước khi chạy.

Codex hỗ trợ chọn corpus, tạo câu hỏi, hiện thực mã, chạy và đối chiếu máy, đề xuất nhãn audit và soạn báo cáo. Người nộp cần đọc lại bằng chứng, xác nhận nhãn thủ công và nắm được cách tính chỉ số trước khi nộp. Nếu người nộp là người chấm duy nhất, nhãn có khả năng chịu thiên lệch do biết cấu hình.
