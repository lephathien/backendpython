# Bài 8: Bảo mật, giám sát & triển khai (Docker & Vercel)

Dự án hoàn thiện ứng dụng FastAPI + AI tích hợp đầy đủ các tiêu chuẩn bảo mật, ghi nhận log/giám sát, đóng gói container hóa với Docker & Docker Compose, và cấu hình triển khai Serverless trên Vercel kết hợp cơ sở dữ liệu đám mây Supabase PostgreSQL.

---

## 📂 Cấu trúc thư mục

```text
Bai8/
├── .env                     # Biến môi trường (ADMIN_TOKEN, DATABASE_URL, LLM_API_KEY, POSTGRES_...)
├── .env.example             # Mẫu biến môi trường an toàn để chia sẻ
├── .gitignore               # Loại trừ .env, __pycache__, log, .venv
├── .dockerignore             # Tối ưu hóa dung lượng build image Docker
├── Dockerfile               # Đóng gói image Python 3.11-slim chạy Uvicorn
├── docker-compose.yml       # Điều phối đồng thời FastAPI (web) và PostgreSQL (db)
├── vercel.json              # Cấu hình triển khai Serverless trên Vercel
├── database.py              # Cấu hình kết nối SQLAlchemy và dependency get_db
├── models.py                # ORM models (Conversation, Message, AIJob)
├── schemas.py               # Pydantic schemas cho API
├── main.py                  # Ứng dụng chính (bảo mật Header Token, logging, routes AI)
├── requirements.txt         # Danh sách thư viện cần thiết
├── static/
│   └── styles.css           # File CSS giao diện
└── templates/
    ├── base.html            # Khung HTML dùng chung
    ├── home.html            # Trang chủ
    ├── summarize.html       # Giao diện tóm tắt tài liệu
    ├── summarize_result.html# Kết quả tóm tắt cho Sync / Async
    ├── job_status.html      # Theo dõi trạng thái background job
    ├── jobs_list.html       # Bảng hiệu năng jobs
    └── chat_llm.html        # Giao diện chat với Gemini
```

---

## 🔒 1. Tính năng Bảo mật & Xác thực

### Header Token Authentication (Khuyên dùng)
Route `/admin/dashboard` được bảo vệ bằng custom header `X-Admin-Token`:
- Kiểm tra qua Postman / cURL:
  ```bash
  curl -H "X-Admin-Token: your_admin_token_here" http://127.0.0.1:8000/admin/dashboard
  ```
- Nếu đúng token: Trả về HTTP 200 `{"message": "Welcome to the admin dashboard."}`
- Nếu thiếu hoặc sai token: Trả về HTTP 401 hoặc 403 `{"detail": "Invalid admin token"}`

### Query Token Authentication (Minh họa hạn chế)
Route `/admin?token=your_admin_token_here` minh họa cơ chế query token.

---

## 📋 2. Ghi nhận lỗi (Logging & Monitoring)

- Route `/summarize/background_with_error_handling` minh họa ghi nhận sự cố:
  1. Ghi log ra console terminal.
  2. Ghi lịch sử lỗi có timestamp ra file [`error_log.txt`](file:///Users/hiencolor/Desktop/FPT%20Polytechic/Backend%20vo%CC%9B%CC%81i%20AI/Demo/Bai8/error_log.txt).
  3. Lưu bản ghi sự cố vào cơ sở dữ liệu `ai_jobs` (`status="failed"`, `error_message=...`).

---

## 🐳 3. Hướng dẫn Triển khai bằng Docker

Chạy đồng thời cả FastAPI và PostgreSQL container mà không cần cài PostgreSQL trên máy:

```bash
cd Bai8
docker compose up --build
```
- Ứng dụng FastAPI: [http://localhost:8000/](http://localhost:8000/)
- API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## ☁️ 4. Hướng dẫn Triển khai trên Vercel & Supabase

1. **Supabase**: Tạo project mới, vào mục Connect chọn **Transaction Pooler** và sao chép chuỗi kết nối `DATABASE_URL`.
2. **GitHub**: Đẩy mã nguồn thư mục `Bai8` lên repository.
3. **Vercel**:
   - Chọn New Project -> Import repository từ GitHub.
   - Thêm biến môi trường:
     - `DATABASE_URL`: chuỗi kết nối từ Supabase.
     - `LLM_API_KEY`: API Key của bạn từ Google AI Studio.
     - `ADMIN_TOKEN`: mã token bảo mật quản trị.
   - Bấm **Deploy**.
