# PROMPTS.md

Every prompt I typed into AI coding assistants for this challenge, in chronological order.
The log was extracted programmatically from the assistants' local session transcripts.

- Prompts are verbatim: wording, spelling and missing Vietnamese diacritics are exactly as typed.
- Assistant replies are not included.
- Attached images are noted but not reproduced.
- A third party's personal name is replaced by `[redacted name]`; nothing else is changed.

Tools: ChatGPT desktop app (Codex) to understand the brief and draft a planning prompt;
Claude Code to plan, run a plan review against Codex, and implement.

## Workflow summary

Written afterwards as a guide to the log below; the prompts themselves follow unedited.

1. **Understand the brief (ChatGPT / Codex).** Read the challenge README and the recruiter's email, list what the submission must contain, and draft a precise planning prompt for Claude Code.
2. **Plan before coding (Claude Code).** Analyse the requirements, separate stated rules from unspecified behaviour, and settle the open decisions: language (Python, standard library only), the invalid-row policy (stop by default, `--skip-invalid` to skip), and how zero-impression campaigns are ranked.
3. **Adversarial plan review.** Run a structured debate in which a separate Codex session reviewed the plan. Three rounds led to exact Decimal accumulation with a 60-digit context, strict CSV parsing with a separate class of structural errors, and a CSV-aware SQLite cross-check.
4. **Scope decision.** Weigh adding a user-facing report against the CLI-only brief, then choose a self-contained static HTML report that adds no dependencies.
5. **Implement and verify.** Implement the plan, run it on the real 1 GB dataset, measure time and memory, cross-check the results with SQLite, and review the report through screenshots.
6. **Polish the report and prepare the submission.** Iterate on the report design, add the plan to the repository, and prepare the commit.

## 1. ChatGPT / Codex: understanding the brief

### 1.1 · 2026-11-06T07:24:01.008Z

_Image attached: screenshot of the recruiter's email (not reproduced; private message)._

### 1.2 · 2026-11-06T07:25:07.483Z

```text
[https://github.com/flinters-vietnam/recruitment/tree/main/fv-sec-001-software-engineer-challenge](https://github.com/flinters-vietnam/recruitment/tree/main/fv-sec-001-software-engineer-challenge)

đọc kỹ readme.md tại repo trên và tóm tắt yêu cầu chức năng, kỹ thuật, các tài liệu cần nop và tiêu chí đánh giá.
```

### 1.3 · 2026-11-06T07:27:06.175Z

```text
vậy theo yêu cầu của ảnh, đối chiếu với readme và nêu rõ yêu cầu được xác định
```

### 1.4 · 2026-11-06T07:29:17.909Z

```text
tạo prompt clear đẻ claude lên plan cho bài test này bao gồm bối cảnh, yêu cầu, ràng buộc, các quyết định cần giải quyết và tiêu chí hoàn thành
```

### 1.5 · 2026-11-06T08:35:58.096Z

```text
đi sâu vào yêu cầu của bài test này và liệt kê clear
```

### 1.6 · 2026-11-06T08:42:56.535Z

```text
Bài test yêu cầu viết một ứng dụng dòng lệnh (CLI), bằng ngôn ngữ tuỳ chọn, để xử lý file `ad_data.csv` dung lượng khoảng 1 GB chứa dữ liệu quảng cáo. Nội dung dưới đây lấy từ README của đề trên GitHub, bản cập nhật ngày 18/03/2026.

**Dữ liệu vào** gồm 6 cột: `campaign_id`, `date`, `impressions`, `clicks`, `spend`, `conversions`. File ZIP được lưu bằng Git LFS.

**Việc phải làm:**

1. **Gộp theo `campaign_id`:** tính 4 tổng là `total_impressions`, `total_clicks`, `total_spend`, `total_conversions`.
2. **Tính hai tỷ lệ:** `CTR = total_clicks / total_impressions` và `CPA = total_spend / total_conversions`. Nếu conversions bằng 0 thì bỏ qua CPA hoặc để null.
3. **Xuất `top10_ctr.csv`:** 10 campaign có CTR cao nhất.
4. **Xuất `top10_cpa.csv`:** 10 campaign có CPA thấp nhất, loại các campaign không có conversion.
5. **Cột đầu ra:** cả hai file có 7 cột `campaign_id,total_impressions,total_clicks,total_spend,total_conversions,CTR,CPA`.

**Yêu cầu kỹ thuật:**

- **Hiệu năng:** xử lý file 1 GB hiệu quả, tiết kiệm bộ nhớ.
- **Cách chạy:** chạy được bằng một lệnh, ví dụ `python aggregator.py --input ad_data.csv --output results/`.

**Repo nộp bài phải có:**

- **Source code** trên GitHub.
- **Hai file kết quả** `top10_ctr.csv` và `top10_cpa.csv`.
- **README:** cách cài đặt, cách chạy, thư viện dùng, thời gian xử lý file 1 GB, và bộ nhớ đỉnh nếu có đo.
- **`PROMPTS.md`** nếu có dùng AI. File phải đặt đúng tên này ở thư mục gốc và chứa prompt nguyên văn, không chỉnh sửa.
- **Không bắt buộc nhưng được khuyến khích:** Dockerfile và benchmark logs.

**Tiêu chí chấm theo mục Code Quality của đề:**

- Kết quả phải chính xác.
- Code sạch, dễ đọc, không có dead code hay code bị comment bỏ.
- Xử lý lỗi: file không tồn tại, dòng hỏng, các trường hợp biên.
- Chú ý hiệu năng và bộ nhớ.
- Có test kiểm tra tính đúng đắn.
- README giải thích các quyết định không hiển nhiên.

**Cách nộp:** gửi link repo GitHub tới `backoffice@flinters.vn`. Theo email bạn nhận được, hạn nộp là 23:59 ngày 07/11/2026 và thời gian làm ước tính 60–90 phút.

Đề không yêu cầu giao diện. Báo cáo HTML là phần bạn chọn thêm. Bài hiện tại đã đáp ứng mọi mục bắt buộc ở trên, trừ hai việc bạn tự làm: đưa repo lên GitHub và gửi email.



claude làm ntn đã chuẩn và đầy đủ yêu cầu chưa?
```

## 2. Claude Code: planning, plan review, implementation

Entries marked **Answer** are options I picked or typed in the assistant's multiple-choice prompts; the question text is the assistant's, the answer is mine.

### 2.1 · Prompt · 2026-11-06T07:31:17.626Z

```text
/mattpocock-skills:grill-with-docs Hãy đọc kỹ đề tuyển dụng sau và lập kế hoạch triển khai bài làm hoàn chỉnh:
https://github.com/flinters-vietnam/recruitment/tree/main/fv-sec-001-software-engineer-challenge

Ở bước này, chỉ phân tích và lập kế hoạch, chưa viết code hoặc tạo repository.

## Bối cảnh

Tôi chọn làm coding challenge của Flinters Vietnam để nộp vòng đánh giá kỹ thuật.

- Email tuyển dụng ước tính thời gian làm bài 60–90 phút.
- Được phép sử dụng AI.
- Hạn nộp trong email: 23:59 ngày 07/11/2026, không ghi múi giờ.
- Tôi cần một giải pháp đúng, dễ chạy, dễ giải thích khi phỏng vấn và phù hợp phạm vi bài tuyển dụng.

## Yêu cầu đã biết

Xây dựng ứng dụng CLI bằng ngôn ngữ tùy chọn, xử lý `ad_data.csv` khoảng 1 GB.

Các cột đầu vào:
`campaign_id,date,impressions,clicks,spend,conversions`

Gộp tất cả dòng theo `campaign_id`, không nhóm theo ngày, để tính:

- `total_impressions`
- `total_clicks`
- `total_spend`
- `total_conversions`
- `CTR = total_clicks / total_impressions`
- `CPA = total_spend / total_conversions`

Tính tỷ lệ từ các tổng, không lấy trung bình tỷ lệ từng dòng.

Xuất:
1. `top10_ctr.csv`: 10 campaign có CTR cao nhất.
2. `top10_cpa.csv`: 10 campaign có CPA thấp nhất; loại campaign có tổng conversions bằng 0.

Cả hai file có các cột:
`campaign_id,total_impressions,total_clicks,total_spend,total_conversions,CTR,CPA`

Repository nộp bài cần có:
- Source code.
- Hai CSV kết quả chạy trên dataset thật.
- Tests kiểm tra tính đúng đắn.
- README: cài đặt, cách chạy, thư viện, thời gian xử lý dataset thật, bộ nhớ đỉnh nếu đo và giải thích các quyết định cần thiết.
- `PROMPTS.md` lưu nguyên văn các prompt đã dùng với AI. Không chỉnh sửa hoặc tự dựng lại lịch sử prompt.
- Dockerfile và benchmark logs là phần khuyến khích, không phải trọng tâm bắt buộc.

Theo README của đề, gửi link repository đến `backoffice@flinters.vn`. Không tự gửi email hoặc publish bất cứ thứ gì trong bước lập kế hoạch.

## Việc cần làm trước khi đề xuất kế hoạch

1. Truy cập và đọc README hiện tại cùng các tệp liên quan. Nếu không truy cập được, nói rõ giới hạn.
2. Phân biệt yêu cầu được ghi rõ trong đề, điểm chưa được quy định và đề xuất của bạn.
3. Kiểm tra cách tải dataset. ZIP được lưu bằng Git LFS; tránh nhầm file con trỏ với ZIP thật.
4. Nếu có workspace hiện tại, kiểm tra ngắn gọn cấu trúc và hướng dẫn liên quan trước khi đề xuất công nghệ.
5. Không khẳng định số dòng, số campaign, độ chính xác của spend hoặc benchmark khi chưa kiểm chứng.

## Những quyết định kế hoạch cần giải quyết

- Chọn ngôn ngữ và thư viện, giải thích ngắn gọn lý do. Nếu chưa có ràng buộc, tự chọn một phương án phù hợp thay vì đưa quá nhiều lựa chọn.
- Cách đọc và tổng hợp dữ liệu mà không tải toàn bộ CSV vào RAM.
- Độ phức tạp thời gian và bộ nhớ; lưu ý bộ nhớ có thể tăng theo số campaign khác nhau.
- Biểu diễn tiền và độ chính xác khi tính toán.
- Xếp hạng bằng giá trị chưa làm tròn; chỉ làm tròn khi ghi kết quả.
- Quy tắc xử lý bằng điểm để đầu ra ổn định.
- Xử lý impressions bằng 0, conversions bằng 0, ít hơn 10 campaign, file rỗng, thiếu header, dữ liệu sai định dạng và đường dẫn không hợp lệ.
- Chính sách với dòng lỗi: dừng hay bỏ qua; giải thích và tránh tạo kết quả thiếu một cách âm thầm.
- Cách kiểm chứng kết quả độc lập và đo thời gian/bộ nhớ trên dataset thật.
- Cách ghi nhận prompt từ thời điểm bắt đầu.

Ưu tiên giải pháp đơn giản, ít phụ thuộc, dễ đọc và đủ nhanh. Không thêm UI, API, database, dịch vụ cloud hoặc xử lý song song nếu chưa có lý do cụ thể.

## Định dạng câu trả lời

Trả lời bằng tiếng Việt, gồm:

1. Tóm tắt phạm vi và checklist yêu cầu nộp bài.
2. Các điểm còn mơ hồ, kèm mặc định đề xuất.
3. Công nghệ và luồng xử lý được chọn.
4. Cấu trúc repository dự kiến.
5. Kế hoạch triển khai theo thứ tự, có thời lượng ước tính và tiêu chí hoàn thành cho từng bước.
6. Danh sách test quan trọng và cách xác minh hai CSV.
7. Kế hoạch benchmark và nội dung cần ghi vào README.
8. Checklist cuối trước khi nộp.

Tách rõ phần cần hoàn thành trong 60–90 phút và phần cải thiện nếu còn thời gian. Nếu mốc này khó đạt, nói rõ phần nào có thể vượt thời gian.

Chỉ hỏi lại những thông tin thực sự chặn việc lập kế hoạch; với quyết định thông thường, nêu giả định và tiếp tục. Kết thúc sau khi đưa kế hoạch, chờ tôi yêu cầu triển khai.
```

### 2.2 · Answer · 2026-11-06T07:35:19.136Z

```text
Question: Chọn ngôn ngữ nào cho bài làm? (máy hiện có Python 3.15 + uv và Node 22; không có Go/Rust/Java)
Answer: Python 3, chỉ stdlib (Recommended)
```

### 2.3 · Answer · 2026-11-06T07:35:19.136Z

```text
Question: Chính sách với dòng lỗi (sai số cột, số âm, không parse được)?
Answer: Mặc định dừng; có cờ --skip-invalid (Recommended)
```

### 2.4 · Answer · 2026-11-06T07:35:19.136Z

```text
Question: Campaign có total_impressions = 0 (CTR không xác định) xử lý thế nào trong top10_ctr?
Answer: Loại khỏi top10_ctr, ghi CTR trống (Recommended)
```

### 2.5 · Answer · 2026-11-06T07:35:19.136Z

```text
Question: Repo bài làm đặt ở đâu và đặt tên gì? (sẽ tạo ở bước triển khai, chưa tạo bây giờ)
Answer: ~/Work/fv-ad-aggregator, GitHub public cùng tên (Recommended)
```

### 2.6 · Prompt · 2026-11-06T07:40:15.236Z

```text
debate plan voi codex đi
```

### 2.7 · CLI command · 2026-11-06T07:49:48.746Z

```text
/model opus
```

### 2.8 · Prompt · 2026-11-06T07:50:01.929Z

```text
check xem codex đã opponent xong chưa?
```

### 2.9 · Answer · 2026-11-06T07:51:47.063Z

```text
Question: Codex chưa vào debate. Bạn muốn làm gì tiếp?
Answer: ping codex xem con hoat dong
```

### 2.10 · Answer · 2026-11-06T07:53:00.534Z

```text
Question: Không chèn được vào phiên Codex đang mở trong app. Làm cách nào để Codex vào vai Opponent?
Answer: Tôi chạy Codex CLI headless
```

### 2.11 · Prompt · 2026-11-06T08:01:34.603Z

```text
file plan đâu?
```

### 2.12 · Prompt · 2026-11-06T08:03:07.252Z

```text
mo file lên
```

### 2.13 · Prompt · 2026-11-06T08:05:52.631Z

```text
bổ sung UI/UX phần kết quả cho plan. chú ý: có show menu link download 2 file csv
```

### 2.14 · Prompt · 2026-11-06T08:09:36.765Z

```text
bài test cho dùng AI nên plan vẫn cần bổ sung thêm UI/UX
```

### 2.15 · Answer · 2026-11-06T08:13:21.803Z

```text
Question: Sau khi cân nhắc, bạn muốn xử lý UI/UX thế nào trong plan?
Answer: sửa lại plan có cần UI/UX
```

### 2.16 · Prompt · 2026-11-06T08:20:47.588Z

```text
implement và bật local chạy test
```

### 2.17 · Prompt · 2026-11-06T08:36:30.543Z

```text
liệt kê chi tiết những file đã làm, kèm chức năng
```

### 2.18 · Prompt · 2026-11-06T08:42:19.817Z

```text
/ui-skill-max giao diện html cần sửa lại cho chuyên nghiệp hơn
```

### 2.19 · Prompt · 2026-11-06T08:50:39.022Z

_Image attached (not reproduced)._

```text
phần này cần highlight lên cho dễ thấy
```

### 2.20 · Prompt · 2026-11-06T08:52:40.603Z

```text
đưa file plan.md vào project và update lại readme cho phù hợp
```

### 2.21 · Prompt · 2026-11-06T08:55:29.503Z

```text
run test local, tạo test case, check lại data xem chính xác chưa và  report kết quả
```

### 2.22 · Prompt · 2026-11-06T10:25:01.323Z

```text
/dev-git `project\PerformanceAggregator`
```