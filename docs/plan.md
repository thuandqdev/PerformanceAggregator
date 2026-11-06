---
name: "Flinters FV-SEC001 — Ad Performance Aggregator implementation plan"
description: "Plan for the Flinters Vietnam coding challenge: streaming Python CLI aggregating a ~1GB ad_data.csv by campaign_id, producing top10_ctr.csv and top10_cpa.csv, with tests, benchmark, README and PROMPTS.md"
status: pending
created: 2026-11-06
debate_revised_at: 2026-11-06
tags:
  - recruitment
  - coding-challenge
  - python
---

# Kế hoạch: Flinters FV-SEC001 — Ad Performance Aggregator

## Bối cảnh

Nộp coding challenge FV-SEC001 (Flinters Vietnam) để qua vòng đánh giá kỹ thuật. Hạn 23:59 ngày 07/11/2026 (email không ghi múi giờ → coi là giờ Việt Nam, tức còn ~1 ngày kể từ hôm nay 06/11). Mục tiêu: giải pháp **đúng, chạy được bằng một lệnh, giải thích được khi phỏng vấn**, nằm trong phạm vi 60–90 phút. Bước này chỉ lập kế hoạch; chưa tạo repo, chưa viết code.

Đã kiểm chứng trực tiếp trên GitHub (06/11/2026):

- README đề: `fv-sec-001-software-engineer-challenge/README.md` (commit mới nhất 2026-03-18 thêm mục Code Quality + PROMPTS.md).
- `ad_data.csv.zip` trong repo là **LFS pointer 134 byte**; file thật `size 362601631` bytes, `sha256 18264bc95be8ce8fb49c219f9ea3f385071fa0f942387982ad89a55f97d90deb`. Tải qua `https://media.githubusercontent.com/media/flinters-vietnam/recruitment/main/fv-sec-001-software-engineer-challenge/ad_data.csv.zip` (HEAD trả 200, `content-length` khớp) hoặc `git lfs pull`.
- `results/` của đề chỉ chứa `.gitkeep`; `.gitignore` của đề bỏ qua `ad_data.csv` và `generator` (nhà tuyển dụng có script sinh dữ liệu — dữ liệu là sinh ngẫu nhiên, không phải dữ liệu thật).
- Máy: Apple M4 Pro, 12 core, 24 GB RAM, 97 GB trống. Có Python 3.15.2, uv 0.11, Node 22, git-lfs 3.6, `/usr/bin/time -l`. **Không có** Go, Rust, Java, Docker, pytest (cài qua uv khi cần).
- Chưa kiểm chứng: số dòng, số campaign, số chữ số thập phân của `spend`, thời gian/bộ nhớ thực tế. Không khẳng định các con số này cho đến khi chạy.

Quyết định Human đã chốt (popup): **Python 3 chỉ stdlib**; **mặc định dừng khi gặp dòng lỗi, có cờ `--skip-invalid`**; **campaign có `total_impressions = 0` bị loại khỏi `top10_ctr`, cột CTR để trống**; repo tại **`~/Work/fv-ad-aggregator`**, GitHub public cùng tên (tạo ở bước triển khai).

**Bổ sung sau debate — UI/UX (Human quyết định, 06/11/2026):** bài làm có phần UI/UX. Agent đã nêu lo ngại (đề chỉ yêu cầu CLI, Code Quality nhấn "no dead code", tăng thời gian) và Human giữ quyết định. Hình thức được chọn để giữ rủi ro thấp: **báo cáo HTML tĩnh tự chứa** do chính CLI sinh ra + **cải thiện UX dòng lệnh**. Không server, không framework, không JS bắt buộc, không phụ thuộc mới — vẫn chỉ stdlib. Xem §3b. Phần này **chưa qua debate** với Codex (debate đóng ở v4).

---

## 1. Phạm vi và checklist nộp bài

### Yêu cầu ghi rõ trong đề

| # | Yêu cầu | Nguồn |
| --- | --- | --- |
| R1 | CLI, ngôn ngữ tuỳ chọn, ví dụ `python aggregator.py --input ad_data.csv --output results/` | README §3 |
| R2 | Gộp theo `campaign_id`: 4 tổng + `CTR = clicks/impressions`, `CPA = spend/conversions`; conversions = 0 → ignore/null CPA | README §1 |
| R3 | `top10_ctr.csv` (CTR cao nhất), `top10_cpa.csv` (CPA thấp nhất, loại conversions = 0); 7 cột đúng thứ tự `campaign_id,total_impressions,total_clicks,total_spend,total_conversions,CTR,CPA` | README §2 |
| R4 | Xử lý hiệu quả file ~1 GB, tối ưu bộ nhớ | README §3 |
| R5 | Repo gồm: source, 2 CSV kết quả, README (setup, cách chạy, thư viện, thời gian xử lý, peak memory nếu đo, giải thích quyết định), tests | README Submission + Code Quality |
| R6 | Kết quả chính xác, code sạch, xử lý lỗi (file thiếu, dòng hỏng, edge case) | Code Quality |
| R7 | `PROMPTS.md` ở root, tên chính xác, prompt nguyên văn không chỉnh sửa | AI Coding Assistants |
| R8 | Tuỳ chọn: Dockerfile, benchmark logs | Submission §4 |

### Checklist nộp bài

- [ ] `aggregator.py` chạy được bằng lệnh y hệt ví dụ trong đề
- [ ] `results/top10_ctr.csv`, `results/top10_cpa.csv` sinh từ dataset thật, commit vào repo
- [ ] `tests/` chạy pass (`uv run pytest`)
- [ ] `README.md`: cài đặt, chạy, thư viện (stdlib + pytest dev), thời gian, peak memory, quyết định
- [ ] `PROMPTS.md` nguyên văn
- [ ] `.gitignore` loại `ad_data.csv*`, `data/`, `.venv`, cache
- [ ] `results/report.html` sinh từ dataset thật, mở được offline, hiển thị đúng ở desktop và mobile (§3b)
- [ ] (tuỳ chọn) `Dockerfile`, `benchmarks/*.log`
- [ ] Repo public, link gửi `backoffice@flinters.vn` (Human tự gửi)

---

## 2. Điểm mơ hồ và mặc định đề xuất

| # | Điểm chưa quy định | Mặc định đề xuất | Lý do |
| --- | --- | --- | --- |
| A1 | Số chữ số thập phân khi ghi | `total_spend` và `CPA`: 2 chữ số; `CTR`: 4 chữ số; làm tròn half-up (helper số nguyên, xem §3) | Khớp bảng ví dụ trong đề (`0.0500`, `20.00`, `12500.50`) |
| A2 | Giá trị "null" của CPA/CTR trong CSV | Ô trống | Đề cho phép "ignore or return null"; ô trống là null phổ biến nhất trong CSV |
| A3 | Xử lý bằng điểm | Khoá phụ `campaign_id` tăng dần (so sánh chuỗi) | Đầu ra ổn định, tái lập được; dễ giải thích |
| A4 | `impressions = 0` | Loại khỏi `top10_ctr`, CTR trống (vẫn có thể xuất hiện trong `top10_cpa`) | Đã chốt; đối xứng với quy tắc CPA của đề |
| A5 | Ít hơn 10 campaign | Ghi số dòng có được, không lỗi | Hợp lý nhất, không làm đầu ra thiếu âm thầm |
| A6 | File rỗng (0 byte) hoặc header sai/thiếu | Lỗi, exit 1, không ghi CSV | Không có header thì không thể biết cột |
| A7 | File chỉ có header | Ghi 2 file chỉ có header, cảnh báo ra stderr, exit 0 | Đầu vào hợp lệ nhưng rỗng |
| A8 | Thứ tự cột / cột thừa | Định vị 6 cột bắt buộc theo tên trong header; cột thừa bỏ qua; thiếu cột bắt buộc → lỗi | Linh hoạt mà vẫn chặt |
| A9 | Dòng lỗi | Hai loại lỗi tách biệt. **Lỗi giá trị dòng** (A10) — mặc định dừng (exit 1, in số dòng + lý do); `--skip-invalid` bỏ qua, đếm, báo tổng số dòng bỏ qua ra stderr. **Lỗi cấu trúc** (A9b) — luôn dừng, kể cả khi có `--skip-invalid` | Đã chốt phần giá trị dòng; phần cấu trúc: sau lỗi quote không còn biết ranh giới bản ghi, bỏ qua sẽ có thể nuốt mất các dòng sau |
| A9b | Định nghĩa "lỗi cấu trúc" | `csv.Error` từ reader `strict=True` (quote sai, field vượt `field_size_limit` mặc định 131072), `UnicodeDecodeError`, `OSError` khi đọc; tổng `spend` vượt miền chính xác (M1, `decimal.Inexact`). Bắt quanh việc lấy dòng kế tiếp, báo `reader.line_num` (dòng vật lý), exit 1, không traceback | Reader mặc định (`strict=False`) chấp nhận `"CMP001"junk` thành `CMP001junk` — đã kiểm bằng probe; `strict=True` báo `',' expected after '"'` |
| A10 | Định nghĩa "lỗi giá trị dòng" | Số cột khác header; `campaign_id` rỗng; `impressions/clicks/conversions` không phải số nguyên base-10 ≥ 0; `spend` không phải Decimal hữu hạn ≥ 0 (từ chối `NaN`, `Infinity`) | Cột `date` **không** validate (không dùng trong tổng hợp) — ghi rõ trong README |
| A11 | Khoảng trắng quanh giá trị, BOM | Chấp nhận (`int()`/`Decimal()` tự strip; mở file `utf-8-sig`) | Robust, chi phí 0 |
| A12 | Múi giờ hạn nộp | Giờ Việt Nam (UTC+7) | Công ty ở Hà Nội; nộp sớm để không phụ thuộc |
| A13 | Nhà tuyển dụng chạy lại code? | Giả định có → README phải chạy được bằng `python3` thuần, không cần uv | uv chỉ cho pytest |
| A14 | Ngôn ngữ của báo cáo HTML | Tiếng Anh | Người đọc là người chấm của Flinters; đề, README và tên cột đều tiếng Anh |
| A15 | Báo cáo HTML bật mặc định hay theo cờ? | Bật mặc định, tắt bằng `--no-html` | Hai CSV bắt buộc luôn được ghi trước; HTML là đầu ra phụ, lỗi khi ghi HTML không làm hỏng CSV |

---

## 3. Công nghệ và luồng xử lý

**Ngôn ngữ:** Python 3 (≥ 3.10), **chỉ stdlib**: `csv`, `decimal`, `fractions`, `argparse`, `pathlib`, `time`, `sys`. Dev-only: `pytest` qua `uv`.

**Vì sao:** khớp ví dụ CLI trong đề; `csv` module là C nên đủ nhanh cho 1 GB đơn luồng; `Decimal`/`Fraction` cho tiền và tỷ lệ chính xác mà không cần thư viện; code ngắn, một file, dễ giải thích. Không dùng pandas/polars (tải cả file hoặc thêm phụ thuộc nặng cho bài 1 lần chạy). Không song song: I/O + parse đơn luồng dự kiến dưới vài phút, thêm multiprocessing làm code khó giải thích hơn lợi ích.

**Luồng xử lý (streaming, một lượt):**

```
open(input, newline="", encoding="utf-8-sig")
→ csv.reader(f, strict=True) → đọc header → map tên cột → index (A8)
→ with decimal.localcontext(prec=60, traps Inexact):   # M1
   for row in reader:                     # O(N) dòng, không giữ dòng nào
     (csv.Error / UnicodeDecodeError / Inexact → lỗi cấu trúc, luôn dừng, A9b)
     validate (A10) → lỗi: raise / skip theo cờ
     acc = totals.setdefault(campaign_id, [0, 0, Decimal(0), 0])
     acc[0] += impressions; acc[1] += clicks; acc[2] += spend; acc[3] += conversions
→ sau vòng lặp: với mỗi campaign (C phần tử)
     ctr = Fraction(clicks, impressions) nếu impressions > 0 else None
     cpa = Fraction(spend) / conversions nếu conversions > 0 else None
           # Fraction(Decimal) chính xác; Fraction(Decimal, int) là TypeError — phải chia sau
→ top10_ctr = sorted(có ctr, key=(-ctr, campaign_id))[:10]
   top10_cpa = sorted(có cpa, key=(cpa, campaign_id))[:10]
→ ghi 2 CSV bằng csv.writer, làm tròn chỉ tại bước format (A1)
→ stderr: số dòng đọc, số dòng bỏ qua, số campaign, thời gian
```

**Độ phức tạp:** thời gian O(N + C log C) với N dòng, C campaign (C log C có thể thay bằng `heapq.nsmallest(10)` O(C log 10) nhưng C nhỏ so với N nên sort đủ và dễ đọc). Bộ nhớ O(C): mỗi campaign ~ 1 key + 4 số; không phụ thuộc N. Rủi ro duy nhất: C rất lớn (hàng triệu campaign) → dict vài trăm MB; ghi nhận trong README là giới hạn đã biết.

**Tiền và độ chính xác — hợp đồng số học:**

- *Miền hỗ trợ:* mỗi tổng `spend` của một campaign tối đa 60 chữ số có nghĩa (phần nguyên + phần thập phân). Số nguyên (`impressions`, `clicks`, `conversions`) là `int` Python, không giới hạn.
- *Cộng dồn:* `Decimal` trong `decimal.localcontext(prec=60)` với `traps[Inexact] = True`. Trong miền hỗ trợ phép cộng là chính xác tuyệt đối. Ngoài miền, phép cộng phát `Inexact` → lỗi cấu trúc có số dòng, exit 1; **không bao giờ làm tròn âm thầm**. Chỉ bẫy `Inexact`, không bẫy `Rounded` (Rounded báo cả khi chỉ bỏ số 0 vô nghĩa). Context mặc định 28 chữ số đã được probe là làm tròn âm thầm `1234567890123456789012345678.90 + 0.01` thành `…679` — đây là lý do phải đặt context tường minh. 60 chữ số dư rất xa cho dữ liệu quảng cáo (ví dụ 10^9 dòng × 10^9 USD vẫn chỉ 20 chữ số); con số được chọn để giải thích dễ, không phải để chạm biên.
- *Tỷ lệ:* `Fraction` từ tổng (CTR = `Fraction(clicks, impressions)`, CPA = `Fraction(total_spend) / conversions`) → xếp hạng chính xác tuyệt đối, bằng điểm thật mới rơi vào khoá phụ.
- *Làm tròn khi ghi:* một helper duy nhất `round_half_up(x: Fraction, places) -> str`, **chỉ dùng số nguyên và chuỗi, không có phép toán Decimal nào** nên không phụ thuộc context: `n = (2·num·10^places + den) // (2·den)` (tức `floor(x·10^places + 1/2)`, x ≥ 0), rồi `whole, frac = divmod(n, 10^places)` và trả `f"{whole}.{frac:0{places}d}"`. Trả chuỗi vì người dùng duy nhất là `csv.writer`. Không dùng `quantize`/`scaleb`: cả hai là phép toán theo context — probe cho thấy `Decimal(123456789012345678901234567891).scaleb(-2)` ở context mặc định ra `…679`. Helper dùng cho cả `total_spend`, CTR, CPA. Đã probe: `…678.91 → 1234567890123456789012345678.91`, `1/8 → 0.13`, `93.70/27 → 3.47`, `640/26000 → 0.0246`, `0.00005 → 0.0001`, `0 → 0.00`, `12500.5 → 12500.50`. Nếu đo thấy `Decimal` parse quá chậm, phương án dự phòng (ghi vào mục "nếu còn thời gian"): parse `spend` thành số nguyên cents khi chuỗi có đúng ≤ 2 chữ số thập phân, fallback `Decimal` khi không — vẫn chính xác.

**CLI:**

```
python3 aggregator.py --input ad_data.csv --output results/ [--skip-invalid]
```

Exit code: 0 thành công; 1 lỗi dữ liệu/header; 2 lỗi tham số hoặc file không tồn tại (argparse). Tạo thư mục output nếu chưa có.

---

## 3b. UI/UX

Hai lớp, đều chỉ dùng stdlib, đều nằm sau phần lõi đã debate (không thay đổi logic tổng hợp).

### Lớp 1 — UX dòng lệnh

| Hạng mục | Hành vi |
| --- | --- |
| `--help` | argparse có `description` + `epilog` với 2 ví dụ lệnh và bảng exit code |
| Tiến độ | Ra **stderr**, cập nhật một dòng (`\r`) mỗi 1.000.000 dòng: số dòng đã đọc, MB đã đọc / tổng MB (từ `f.buffer.tell()` so với `os.path.getsize`), tốc độ dòng/giây. Chỉ bật khi `sys.stderr.isatty()`; tắt bằng `--quiet`. Không bao giờ in ra stdout |
| Tóm tắt cuối | Khối ngắn ra stderr: dòng đọc, dòng bỏ qua, số campaign, thời gian, đường dẫn 3 file đã ghi |
| Thông báo lỗi | Một dòng `error: <file>:<line>: <lý do>`, không traceback, gợi ý `--skip-invalid` khi lỗi thuộc loại giá trị dòng |
| Ghi file an toàn | Ghi vào file tạm cùng thư mục rồi `os.replace` → không để lại CSV dở dang khi bị lỗi hoặc Ctrl+C |
| Ctrl+C | Bắt `KeyboardInterrupt`, in `interrupted`, exit 130, không traceback |

### Lớp 2 — Báo cáo HTML tĩnh `results/report.html`

**Mục đích:** người chấm mở một file, thấy ngay kết quả và số liệu chạy, không cần đọc CSV thô.

**Kỹ thuật:** module riêng `report.py`, hàm thuần `render_report(summary, top_ctr, top_cpa) -> str`, dựng HTML bằng `string.Template` + `html.escape` cho **mọi** giá trị lấy từ dữ liệu (`campaign_id` là chuỗi tuỳ ý từ CSV → chống chèn HTML). CSS inline trong `<style>`, không tải tài nguyên ngoài, không JS → mở offline, không lỗi CSP, chụp được bằng headless browser. Giá trị số dùng **đúng chuỗi đã định dạng cho CSV** (cùng `round_half_up`) → HTML và CSV không thể lệch nhau.

**Bố cục (một trang, từ trên xuống):**

1. Tiêu đề "Ad Performance Report" + tên file input + thời điểm chạy.
2. Hàng thẻ tóm tắt: rows processed, rows skipped (tô cảnh báo nếu > 0), campaigns, processing time, peak memory nếu đo được trong tiến trình (`resource.getrusage`, ghi chú đơn vị khác nhau macOS/Linux).
3. Bảng "Top 10 by CTR": 7 cột như CSV; cột CTR có thanh ngang CSS (`width` theo CTR / CTR lớn nhất trong bảng) để so sánh bằng mắt.
4. Bảng "Top 10 by lowest CPA": tương tự, thanh theo CPA; ô CTR/CPA null hiển thị `—` kèm `title` giải thích.
5. Chú thích cuối: định nghĩa CTR/CPA, quy tắc bằng điểm, quy tắc loại (0 impressions / 0 conversions), làm tròn half-up.

**Yêu cầu UX của trang:** số căn phải, font `tabular-nums`; header bảng dính khi cuộn; bảng cuộn ngang trong khung riêng ở màn hẹp (không cuộn cả trang); khoảng đệm 16px ở mobile; màu qua biến CSS `:root`, có `prefers-color-scheme: dark`; độ tương phản chữ ≥ 4.5:1; bảng dùng `<caption>`, `<th scope>` cho trình đọc màn hình; bảng rỗng (< 1 campaign đủ điều kiện) hiển thị câu "No eligible campaigns" thay vì bảng trống.

**Không làm:** server, framework, biểu đồ JS, lọc/sắp xếp tương tác, upload file qua trình duyệt.

---

## 4. Cấu trúc repository dự kiến

```
fv-ad-aggregator/
├── aggregator.py            # logic + CLI (~230 dòng): parse_header, parse_row, aggregate, rank, write_results, progress, main
├── report.py                # render_report(): HTML tĩnh tự chứa (~120 dòng gồm template + CSS)
├── tests/
│   ├── test_aggregator.py   # unit + end-to-end qua tmp_path
│   ├── test_report.py       # escape, khớp số với CSV, trạng thái rỗng
│   └── fixtures/            # CSV nhỏ nếu cần (phần lớn tạo inline trong test)
├── results/
│   ├── top10_ctr.csv        # chạy trên dataset thật
│   ├── top10_cpa.csv
│   └── report.html          # báo cáo HTML từ cùng lần chạy
├── docs/
│   └── report-1280.png, report-375.png   # ảnh chụp báo cáo cho README
├── benchmarks/              # (tuỳ chọn) log /usr/bin/time -l, 3 lần chạy
├── scripts/
│   └── crosscheck.sql       # tổng hợp độc lập bằng sqlite3 (CSV-aware) để đối chiếu
├── data/                    # gitignored: ad_data.csv.zip, ad_data.csv
├── pyproject.toml           # metadata + dependency-groups dev = ["pytest"]
├── Dockerfile               # (tuỳ chọn)
├── .gitignore
├── README.md
└── PROMPTS.md
```

Không có `__init__.py`/package: một module, test import trực tiếp (`sys.path` qua `pyproject` `[tool.pytest.ini_options] pythonpath = ["."]`).

---

## 5. Kế hoạch triển khai theo thứ tự

### Phần bắt buộc (mục tiêu 60–90 phút làm việc, chưa tính thời gian chờ tải/chạy)

| Bước | Việc | Ước tính | Tiêu chí hoàn thành |
| --- | --- | --- | --- |
| 0 | Khởi tạo: `mkdir ~/Work/fv-ad-aggregator`, `git init`, `.gitignore`, `pyproject.toml`, tạo `PROMPTS.md` ngay với prompt đầu tiên của phiên này. **Song song:** tải ZIP vào `data/` (curl URL media.githubusercontent, chạy nền), kiểm `shasum -a 256` khớp oid LFS, `unzip` | 10′ (+ tải nền) | Repo trống commit được; `data/ad_data.csv` tồn tại, sha256 ZIP khớp `18264bc9…`; `head -3 data/ad_data.csv` đúng 6 cột |
| 1 | Viết `aggregator.py`: header map, validate dòng, tích luỹ, xếp hạng, ghi file, CLI, tóm tắt stderr | 25′ | Chạy trên 5 dòng ví dụ của đề cho đúng tổng tay tính (CMP001: 26000/640/93.70/27) |
| 2 | Viết `tests/test_aggregator.py` theo danh sách mục 6 | 15′ | `uv run pytest` xanh toàn bộ |
| 3 | Chạy dataset thật: `/usr/bin/time -l python3 aggregator.py --input data/ad_data.csv --output results/` | 5′ làm + chờ | 2 file trong `results/`, ghi lại real time + max RSS; nếu dừng vì dòng lỗi → xem dòng, quyết định có dùng `--skip-invalid` và ghi vào README |
| 4 | Đối chiếu độc lập bằng `scripts/crosscheck.sql` (sqlite3) — xem mục 6 | 5′ + chờ | Top 10 campaign_id và thứ tự khớp; tổng nguyên khớp tuyệt đối; spend lệch < 0.01; số dòng sqlite đếm = số dòng aggregator báo |
| 5 | **UX dòng lệnh** (§3b lớp 1): help/epilog, tiến độ stderr, `--quiet`, ghi file tạm + `os.replace`, Ctrl+C | 10′ | `--help` có ví dụ; chạy file thật thấy tiến độ trên terminal, không thấy khi `2>file`; kill giữa chừng không để lại CSV dở |
| 6 | **Báo cáo HTML** (§3b lớp 2): `report.py`, `--no-html`, `tests/test_report.py` | 25′ | Test xanh; `results/report.html` từ dataset thật; ảnh chụp headless Chrome ở 1280px và 375px không vỡ layout, không cuộn ngang cả trang, cả light và dark |
| 7 | README (thêm mục Report + ảnh chụp) + hoàn thiện PROMPTS.md + commit + tạo repo GitHub public + push | 15′ | README có đủ 6 mục của đề + mục Report; `git status` sạch; link repo mở được ở cửa sổ ẩn danh |

Tổng ~110′ làm việc (lõi ~75′ + UI/UX ~35′). **Vượt mốc 60–90 phút khoảng 20–35 phút, do phần UI/UX.** Thứ tự bảo vệ bài nộp: bước 1–4 tạo ra bài hợp lệ trước; commit một bản nộp được ngay sau bước 4, rồi mới làm bước 5–6. Nếu hết thời gian ở bước 6, bỏ HTML và nộp bản sau bước 5. Thời gian chờ (tải 362 MB, unzip, 1–3 lần chạy 1 GB, import sqlite3 để đối chiếu) nằm ngoài, dự kiến thêm 10–20′ tuỳ mạng. **Rủi ro vượt mốc:** bước 3 nếu dataset thật có dòng lỗi bất ngờ hoặc Decimal quá chậm (phải chuyển sang cents) → +15′.

### Phần cải thiện nếu còn thời gian (làm sau khi đã có bản nộp được)

1. `benchmarks/`: 3 lần chạy, lưu log `/usr/bin/time -l`, ghi median vào README.
2. `Dockerfile` 5 dòng (`python:3.13-slim`, `COPY aggregator.py`, `ENTRYPOINT`). **Không có Docker trên máy** → ghi rõ trong README là chưa build thử tại máy local, hoặc bỏ qua nếu không muốn nộp thứ chưa kiểm chứng.
3. Tối ưu parse `spend` sang cents (chỉ nếu benchmark cho thấy Decimal chiếm phần lớn thời gian; đo bằng `cProfile` trước khi đổi).
4. GitHub Actions chạy pytest (1 file YAML).
5. Test property nhỏ: sinh dữ liệu ngẫu nhiên, so với tổng hợp bằng dict thuần.

---

## 6. Test quan trọng và cách xác minh hai CSV

### Danh sách test (pytest, mỗi test dựng CSV nhỏ trong `tmp_path`)

1. **Ví dụ trong đề** (5 dòng) → tổng từng campaign đúng, nội dung file khớp từng ký tự với chuỗi kỳ vọng (header, thứ tự, format số).
2. **Tỷ lệ từ tổng, không phải trung bình tỷ lệ** — dựng 2 dòng cùng campaign có CTR dòng 0.5 và 0.01 nhưng CTR tổng khác trung bình 0.255.
3. **conversions = 0** → CPA trống, không có trong `top10_cpa`, vẫn có trong `top10_ctr`.
4. **impressions = 0** → CTR trống, không có trong `top10_ctr`, vẫn có trong `top10_cpa`.
5. **Bằng điểm** → thứ tự theo `campaign_id` tăng dần.
6. **Xếp hạng bằng giá trị chưa làm tròn** — hai CTR làm tròn 4 chữ số bằng nhau nhưng thứ tự đúng theo giá trị thật.
7. **Ít hơn 10 campaign** → ghi đúng số dòng có.
8. **Chỉ header** → 2 file chỉ header, exit 0.
9. **File rỗng / thiếu cột bắt buộc** → exit 1, thông báo nêu tên cột thiếu.
10. **Dòng lỗi** (thiếu cột, số âm, `"abc"`, `"12.0"` cho integer) → mặc định exit 1 kèm số dòng; với `--skip-invalid` → bỏ qua, số dòng bỏ qua báo ra stderr, kết quả chỉ từ dòng hợp lệ.
11. **Chính xác thập phân** — spend `0.10` + `0.20` ghi `0.30`; `round_half_up` đúng ở điểm giữa (`1/8` → `0.13`, CTR `0.00005` → `0.0001`).
12. **Biên độ chính xác** — `1234567890123456789012345678.90` + `0.01` cho ra **ô `total_spend` trong file CSV** đúng `1234567890123456789012345678.91` (kiểm toàn bộ chuỗi đầu ra, không chỉ bộ cộng dồn; context mặc định hoặc `scaleb` sẽ ra `…679`); một tổng vượt 60 chữ số có nghĩa → exit 1 với thông báo, không traceback.
13. **Lỗi cấu trúc CSV** — dòng `"CMP001"junk,...` → exit 1 kèm số dòng, **kể cả khi có `--skip-invalid`**; không có file output nào được ghi.
14. **Cột đảo thứ tự / cột thừa / BOM** → vẫn đúng.
15. **Đường dẫn input không tồn tại** → exit ≠ 0, không tạo file output.

**Test cho UI/UX (`tests/test_report.py` + bổ sung end-to-end):**

16. **Chống chèn HTML** — `campaign_id` = `<script>alert(1)</script>` xuất hiện dạng đã escape, không có thẻ `<script>` trong output.
17. **HTML khớp CSV** — mọi giá trị số trong bảng HTML bằng đúng chuỗi trong ô CSV tương ứng (parse lại CSV và tìm trong HTML).
18. **Trạng thái rỗng** — không có campaign đủ điều kiện CPA → HTML có "No eligible campaigns", CSV chỉ có header.
19. **Null hiển thị** — campaign 0 conversions trong bảng CTR hiển thị `—` ở cột CPA.
20. **Tự chứa** — HTML không chứa `http://`, `https://`, `<script`, `<link` (không tài nguyên ngoài, không JS).
21. **`--no-html`** → chỉ 2 CSV được ghi. **`--quiet`** và stderr không phải TTY → không có dòng tiến độ; stdout luôn rỗng.
22. **Không để lại file dở** — lỗi cấu trúc ở giữa file → thư mục output không có CSV/HTML mới và không có file tạm.

### Xác minh hai CSV trên dataset thật (độc lập với code)

- `scripts/crosscheck.sql`, chạy bằng `sqlite3 :memory: < scripts/crosscheck.sql`: `.import --csv data/ad_data.csv ad` (parser CSV của sqlite hiểu quote, header theo tên cột nên không phụ thuộc thứ tự cột), rồi `GROUP BY campaign_id` với `CAST(... AS INTEGER)` / `CAST(spend AS REAL)`, tính CTR/CPA, `ORDER BY` + `LIMIT 10` cho mỗi loại → so với `results/`. Đây là một implementation độc lập (engine khác, ngôn ngữ khác) nên lỗi logic của aggregator không lặp lại ở đây. SQLite cộng `REAL` là double nên **tổng nguyên so khớp tuyệt đối, `total_spend` so với dung sai 0.01**; thứ tự top 10 phải trùng (nếu lệch chỉ do bằng điểm sát nút, giải thích bằng giá trị thật — bằng chứng xếp hạng chính xác vẫn là `Fraction` trong aggregator).
- Kiểm tra bất biến: 2 file đúng 7 cột, ≤ 10 dòng dữ liệu, `top10_cpa` không có `total_conversions = 0`, CTR giảm dần / CPA tăng dần, mỗi dòng `CTR ≈ clicks/impressions` và `CPA ≈ spend/conversions` tính lại từ chính dòng đó.
- Số dòng đọc được (stderr) so với `SELECT count(*) FROM ad` của sqlite (− số dòng bỏ qua nếu có). Không dùng `wc -l` vì một bản ghi CSV có quote có thể trải nhiều dòng vật lý.

---

## 7. Benchmark và nội dung README

**Cách đo:** `/usr/bin/time -l python3 aggregator.py --input data/ad_data.csv --output results/ 2> benchmarks/run-N.log` — lấy `real` và `maximum resident set size` (byte, macOS). Chạy 3 lần sau khi file đã được cache, ghi median; ghi thêm lần đầu (cold) nếu khác nhiều. Chương trình tự in elapsed + số dòng ra stderr để có số liệu không phụ thuộc OS.

**README gồm:**

1. Tóm tắt bài toán, 1 đoạn.
2. Setup: yêu cầu Python ≥ 3.10, không cần cài gì để chạy; `uv sync` / `pip install pytest` để test.
3. Cách chạy: lệnh chính, cờ `--skip-invalid`, exit code, ví dụ output stderr.
4. Cách lấy dataset: curl URL LFS + sha256 kiểm chứng + unzip (vì ZIP trên repo gốc là pointer LFS).
5. Thư viện: stdlib (liệt kê module); pytest dev.
6. Kết quả benchmark: bảng máy (M4 Pro, 24 GB, Python 3.15.2, macOS), thời gian, peak RSS, số dòng, số campaign — **chỉ điền số đã đo**.
7. Thiết kế & quyết định: streaming một lượt O(N)/O(C); hợp đồng số học (Decimal prec 60 + bẫy Inexact, Fraction, `round_half_up` chỉ dùng số nguyên + chuỗi, không phụ thuộc Decimal context); làm tròn khi ghi; quy tắc bằng điểm; CTR/CPA null; hai loại lỗi (giá trị dòng có thể skip, cấu trúc CSV luôn dừng); không validate `date`; vì sao không song song/pandas; giới hạn đã biết (C rất lớn).
8. Tests: lệnh chạy, danh sách ngắn những gì được kiểm.
9. Đối chiếu độc lập: lệnh sqlite3 (`scripts/crosscheck.sql`) và kết quả so khớp.
10. Report: một câu về `report.html`, cờ `--no-html`/`--quiet`, 2 ảnh chụp (desktop, mobile), và lý do chọn HTML tĩnh thay vì web app (không server, không phụ thuộc, mở offline).
10. (nếu có) Docker, benchmark logs.

---

## 8. PROMPTS.md — cách ghi nhận từ đầu

- Tạo file ngay ở bước 0, trước khi viết code. Nội dung: công cụ (Claude Code, model Claude Fable 5.1), ngày, rồi **mọi prompt Human đã gõ, nguyên văn, theo thứ tự thời gian**, bắt đầu từ prompt lập kế hoạch này (gồm cả việc gọi `/mattpocock-skills:grill-with-docs` và phần tham số), kèm các câu trả lời Human chọn trong popup (ghi là lựa chọn, vì đó là input của Human).
- Lấy nguyên văn từ transcript Claude Code (`~/.claude/projects/-Users-ThuanDQ-Work-aweave/*.jsonl`, lọc message `role=user`) thay vì gõ lại — đảm bảo "as-is". Nếu phiên triển khai là phiên mới, nối tiếp tục. Không chèn prompt tưởng tượng, không sửa chính tả, giữ tiếng Việt.
- Không ghi phản hồi của Agent (đề chỉ yêu cầu prompt); có thể thêm 1 dòng mô tả ngắn mỗi prompt dùng để làm gì — tách biệt rõ với phần nguyên văn.

---

## 9. Checklist cuối trước khi nộp

- [ ] `git clone` repo vào thư mục mới, chạy đúng lệnh trong README trên bản clone → kết quả giống `results/` đã commit
- [ ] `uv run pytest` xanh trên bản clone
- [ ] `results/*.csv`: 7 cột, ≤ 10 dòng, không có conversions = 0 trong cpa, số làm tròn đúng định dạng
- [ ] README không chứa số liệu chưa đo; đường dẫn/lệnh copy-paste chạy được
- [ ] `PROMPTS.md` tồn tại, tên chính xác, nguyên văn
- [ ] `.gitignore` chặn `data/`, `ad_data.csv*`; `git ls-files` không có file > 1 MB
- [ ] Không dead code, không comment bị bỏ, không `print` debug
- [ ] `results/report.html` mở bằng trình duyệt ở chế độ offline; số liệu trùng 2 CSV; ảnh chụp trong README là ảnh của chính lần chạy đã commit
- [ ] Repo public; mở link ở cửa sổ ẩn danh
- [ ] Human gửi email tới `backoffice@flinters.vn` trước 23:59 07/11/2026 (giờ VN); Agent không gửi

## Xác minh (sau triển khai)

Chạy `uv run pytest`; chạy lệnh thật với `/usr/bin/time -l`; chạy `scripts/crosscheck.sql` bằng sqlite3 và so sánh; chụp `results/report.html` bằng chrome-headless-shell ở 1280px và 375px, light và dark, rồi xem ảnh; clone lại repo và chạy lại từ đầu theo README.
