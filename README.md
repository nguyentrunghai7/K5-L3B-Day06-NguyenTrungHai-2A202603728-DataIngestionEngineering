# Day 06 · Data Ingestion Engineering

**Lab cá nhân** · **4 giờ** · **Dữ liệu tự chọn**

Biến tài liệu thành kho tri thức có thể truy xuất cho AI agent, rồi đo xem cách chuẩn bị dữ liệu nào hiệu quả nhất.

| 📄 Dữ liệu | 🧩 Chiến lược | 🎯 Benchmark |
|---|---|---|
| Tối thiểu **30 trang nội dung** | Tối thiểu **3 cấu hình** | Tối thiểu **20 câu hỏi** |

## Chạy bài làm với Chroma local

Bài làm dùng 55 chương của *Emma* (Jane Austen) từ [Project Gutenberg #158](https://www.gutenberg.org/ebooks/158). Mỗi chương là một đơn vị nguồn, đối chiếu được bằng tập, chương và dòng trong [manifest](data/manifest.json). Tệp nguồn và model được tải lần đầu. Tệp nguồn phải khớp SHA-256 trong manifest. Nếu Gutenberg cập nhật tệp, cần lấy lại đúng snapshot và đặt tại `data/raw/158.txt` để tái lập số liệu. Không cần Docker hoặc API key.

Chạy từ thư mục gốc trên PowerShell với Python 3.11.

```powershell
python -m venv starter/.venv
& starter/.venv/Scripts/python -m pip install -r starter/requirements-lab.txt
$env:HF_HUB_DISABLE_XET = '1'
& starter/.venv/Scripts/python -m starter.src.run
```

- A dùng cửa sổ 500 ký tự, overlap 50. B ghép các đoạn và giới hạn 500 ký tự, ưu tiên cắt đoạn dài tại câu. C dùng chung index B và lọc `volume` khi người đọc chọn phạm vi trước.
- Model `BAAI/bge-small-en-v1.5` chạy ONNX qua [FastEmbed](https://qdrant.github.io/fastembed/examples/Supported_Models/) với 384 chiều. Chroma lưu index HNSW cosine trong `.lab06/chroma/` và model được lưu trong `.lab06/models/`.
- Collection được đặt tên theo fingerprint của chunk và model. Khi nội dung thay đổi, lần chạy dùng collection mới. Các snapshot cũ vẫn còn trên đĩa và truy xuất chỉ dùng collection của lần chạy hiện tại. Khi nạp lại cùng dữ liệu, code kiểm tra chính xác tập ID và tái sử dụng vector.
- [Bộ benchmark](benchmark/README.md) ghi cách chia dev/test và tiêu chí chọn. [Kết quả](results/) gồm chỉ số, trace, log và các mẫu audit. Để chạy kiểm chứng riêng, thêm `--results .lab06/recheck` vào lệnh chạy.
- [Báo cáo](report/individual/2A2026037228_NguyenTrungHai.md) và [nhật ký thí nghiệm](artifacts/experiment_log.csv) ghi kết quả và các phần cần xác nhận trước khi nộp.

## Bắt đầu nhanh

Dùng [starter PostgreSQL + pgvector](starter/README.md) để dựng database và hoàn thiện các hàm TODO, hoặc tự chọn vector store tương đương. Starter chỉ là khung: **bạn tự hiện thực pipeline và benchmark**.

## 1. Xây pipeline

![Đọc tài liệu, chuẩn hóa, chia chunk, tạo vector, lưu và kiểm tra](assets/ingestion-pipeline.svg)

Chọn tài liệu được phép sử dụng; giữ **ID tài liệu, nguồn, trang/vị trí** và metadata phù hợp. Dùng embedding model thật qua API hoặc chạy local; lưu và truy xuất bằng pgvector, Qdrant, Chroma hoặc một store tương đương.

## 2. So sánh và đánh giá

![Ba chiến lược được đánh giá trên cùng corpus và benchmark dev/test](assets/benchmark-workflow.svg)

Dùng cùng dữ liệu, model và câu hỏi cho cả ba cấu hình. Tách **15 câu dev / 5 câu test** trước khi chạy; chọn cấu hình trên dev, rồi đánh giá test sau khi cố định. Mỗi câu hỏi cần có đoạn bằng chứng và trang nguồn; thiết kế bộ câu hỏi và đánh giá theo [BENCHMARK.md](BENCHMARK.md).

Đánh giá theo năm khía cạnh: **độ chính xác truy xuất**, **tính mạch lạc của chunk**, **tính hữu dụng của metadata**, **chất lượng grounding** và **tác động của chiến lược dữ liệu**. Giải thích lựa chọn bằng kết quả, ví dụ lỗi và các đánh đổi.

## 3. Chuẩn bị bài nộp

1. Chạy pipeline và lưu cấu hình, kết quả top-3, trace cùng nhãn đánh giá thủ công.
2. Điền [thông tin học viên](STUDENT.md), [nhật ký thí nghiệm](artifacts/experiment_log.csv) và bản sao [mẫu báo cáo cá nhân](report/individual/2A2026037228_NguyenTrungHai.md).
3. Kiểm tra mã nguồn, cách chạy, manifest dữ liệu và checklist trong [SUBMISSION.md](SUBMISSION.md).

## Tài liệu hướng dẫn

| Bạn cần tìm | Tài liệu |
|---|---|
| Kiểm tra hạ tầng PostgreSQL + pgvector tùy chọn | [starter/README.md](starter/README.md) |
| Các bước làm và cách tính chỉ số | [GUIDE.md](GUIDE.md) |
| Tiến độ trong 4 giờ | [CHECKPOINTS.md](CHECKPOINTS.md) |
| Năm tiêu chí benchmark và bộ câu hỏi | [BENCHMARK.md](BENCHMARK.md) |
| Tiêu chí chấm điểm | [RUBRIC.md](RUBRIC.md) |
| Quy tắc sử dụng dữ liệu, AI và API | [RULES.md](RULES.md) |
| Cách nộp bài | [SUBMISSION.md](SUBMISSION.md) |

[data/format-example.json](data/format-example.json) chỉ minh họa định dạng, không phải corpus đủ điều kiện. Bài làm hiện thực pipeline và benchmark trong `starter/src/`. Chatbot là tùy chọn.
