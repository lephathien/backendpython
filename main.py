import os, time
from datetime import datetime, timezone
from typing import Annotated
import httpx, requests
from dotenv import load_dotenv

from fastapi import BackgroundTasks, Depends, FastAPI, Form, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from database import Base, SessionLocal, engine, get_db
from models import AIJob

load_dotenv()                                                         # Nạp biến môi trường từ file .env
app = FastAPI(title="FastAPI + AI Demo (Bài 8: Bảo mật, Giám sát & Triển khai)")

try: Base.metadata.create_all(bind=engine)                            # Tự động tạo bảng PostgreSQL nếu kết nối sẵn sàng
except Exception as e: print(f"[Warning] DB: {e}")

app.mount("/static", StaticFiles(directory="static"), name="static")  # Mount thư mục chứa tài nguyên tĩnh CSS/JS
templates = Jinja2Templates(directory="templates")                    # Cấu hình render giao diện Jinja2

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN", "your_admin_token_here")       # Token quản trị bảo vệ route nhạy cảm
LLM_API_KEY = os.getenv("LLM_API_KEY", "")                            # API Key của dịch vụ LLM
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")                # Tên model mặc định
LLM_API_URL = os.getenv(                                              # URL endpoint API sinh nội dung của Gemini
    "LLM_API_URL",
    f"https://generativelanguage.googleapis.com/v1beta/models/{LLM_MODEL}:generateContent"
)


# --- PHẦN 1: BẢO MẬT & XÁC THỰC ROUTE (SECURITY) ---
async def verify_admin_token(x_admin_token: Annotated[str | None, Header()] = None):
    if not x_admin_token:                                             # Kiểm tra xem client có gửi header hay không
        raise HTTPException(status_code=401, detail="X-Admin-Token header missing")
    if x_admin_token != ADMIN_TOKEN:                                  # Kiểm tra tính hợp lệ của token
        raise HTTPException(status_code=403, detail="Invalid admin token")
    return x_admin_token


@app.get("/admin/dashboard")
async def admin_dashboard(token: str = Depends(verify_admin_token)):  # Route quản trị được bảo vệ an toàn bằng Header Token
    return JSONResponse(content={"message": "Welcome to the admin dashboard."})


@app.get("/admin", response_class=JSONResponse)
def admin_dashboard_query(token: str = None):                         # Route quản trị minh họa bảo vệ bằng Query Token trên URL
    if token != ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="Forbidden")      # Trả về mã lỗi 403 nếu sai hoặc thiếu token
    return JSONResponse(content={"message": "Welcome to the admin dashboard."})


# --- PHẦN 2: LOGGING & MONITORING GIÁM SÁT LỖI ---
@app.post("/summarize/background_with_error_handling")
def summarize_background_with_error_handling(request: Request):       # Minh họa ghi log lỗi đồng thời ra console, file và database
    try:
        raise ValueError("Simulated error for testing logging.")      # Giả lập lỗi ngoại lệ để kiểm tra hệ thống ghi log
    except Exception as e:
        print(f"Error occurred: {str(e)}")                            # 1. Ghi log cảnh báo ra màn hình console máy chủ
        with open("error_log.txt", "a") as log_file:                  # 2. Ghi nối tiếp thông tin lỗi vào tệp error_log.txt
            log_file.write(f"{datetime.utcnow()}: {str(e)}\n")

        db = SessionLocal()                                           # 3. Mở session riêng để lưu sự cố vào CSDL
        try:
            now = datetime.now(timezone.utc)
            error_job = AIJob(
                job_type="summary", mode="background", status="failed",
                input_text="Error during background task", error_message=str(e),
                started_at=now, finished_at=now
            )
            db.add(error_job); db.commit()
        finally:
            db.close()

        raise HTTPException(status_code=500, detail="Internal Server Error")


# --- PHẦN 3: XỬ LÝ GỌI LLM & TÁC VỤ NỀN ---
def build_payload_from_text(user_text: str):
    prompt = (                                                        # Định hình câu lệnh yêu cầu tóm tắt tài liệu
        "Hãy tóm tắt tài liệu sau theo 3 phần: ý chính, kỹ thuật quan trọng, gợi ý trình bày.\n\n"
        f"Tài liệu:\n{user_text}"
    )
    return {
        "systemInstruction": {"parts": [{"text": "Bạn là trợ lý học tập cho sinh viên cao đẳng ngành lập trình. Ưu tiên tiếng Việt, ngắn gọn, dễ hiểu."}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],  # Dữ liệu nội dung gửi cho Gemini
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 2048}  # Đủ ngân sách cho thinking và câu trả lời
    }


def extract_text_from_response(data: dict) -> str:
    candidates = data.get("candidates", [])
    if not candidates: return "Không có phản hồi từ Gemini."
    parts = candidates[0].get("content", {}).get("parts", [])         # Lấy danh sách các parts trong phản hồi
    texts = [p.get("text") for p in parts if p.get("text")]           # Trích xuất văn bản từ từng part
    return "\n".join(texts).strip() if texts else "Gemini không trả về nội dung."


def call_llm_from_text(user_text: str) -> str:
    payload = build_payload_from_text(user_text)                      # Xây dựng payload đồng bộ (Sync)
    headers = {"Content-Type": "application/json", "x-goog-api-key": LLM_API_KEY}
    response = requests.post(LLM_API_URL, headers=headers, json=payload, timeout=90)  # Gửi request đồng bộ chặn luồng
    response.raise_for_status()
    return extract_text_from_response(response.json())


async def call_llm_from_text_async(user_text: str) -> str:
    payload = build_payload_from_text(user_text)                      # Xây dựng payload bất đồng bộ (Async)
    headers = {"Content-Type": "application/json", "x-goog-api-key": LLM_API_KEY}
    async with httpx.AsyncClient(timeout=90) as client:               # Dùng AsyncClient để không chặn luồng I/O
        response = await client.post(LLM_API_URL, headers=headers, json=payload)  # Chờ phản hồi bất đồng bộ bằng await
        response.raise_for_status()
        return extract_text_from_response(response.json())


def create_job(db: Session, input_text: str, job_type: str = "summary", mode: str = "background") -> AIJob:
    job = AIJob(input_text=input_text, job_type=job_type, mode=mode, status="pending")  # Khởi tạo job trạng thái pending
    db.add(job); db.commit(); db.refresh(job)                         # Lưu vào DB để lấy job.id ngay lập tức
    return job


def save_completed_job(db: Session, input_text: str, result_text: str, mode: str, ms: int, status: str = "done", err: str | None = None) -> AIJob:
    now = datetime.now(timezone.utc)
    job = AIJob(input_text=input_text, result_text=result_text, mode=mode, status=status, error_message=err, processing_time_ms=ms, started_at=now, finished_at=now)
    db.add(job); db.commit(); db.refresh(job)                         # Ghi nhận kết quả xử lý của chế độ sync/async
    return job


def run_summary_job(job_id: int):
    db = SessionLocal()                                               # Mở session DB riêng cho tác vụ chạy ngầm
    started = time.perf_counter()                                     # Bấm giờ đo thời gian tác vụ nền
    try:
        job = db.query(AIJob).filter(AIJob.id == job_id).first()
        if not job: return

        job.status = "running"                                        # Chuyển trạng thái sang running khi bắt đầu xử lý
        job.started_at = datetime.now(timezone.utc)
        db.commit()

        job.result_text = call_llm_from_text(job.input_text)          # Gọi LLM tóm tắt tài liệu
        job.processing_time_ms = int((time.perf_counter() - started) * 1000)
        job.status = "done"                                           # Chuyển trạng thái sang done khi hoàn tất
        job.finished_at = datetime.now(timezone.utc)
        db.commit()
    except Exception as e:
        job = db.query(AIJob).filter(AIJob.id == job_id).first()
        if job:
            job.status, job.error_message = "failed", str(e)          # Đánh dấu failed nếu xảy ra ngoại lệ
            job.processing_time_ms = int((time.perf_counter() - started) * 1000)
            job.finished_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()                                                    # Đảm bảo luôn đóng session sau khi chạy xong


# --- PHẦN 4: ROUTE GIAO DIỆN WEB (SSR) ---
@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("home.html", {"request": request})  # Hiển thị trang chủ giới thiệu


@app.get("/summarize", response_class=HTMLResponse)
def summarize_page(request: Request):
    return templates.TemplateResponse("summarize.html", {"request": request})  # Hiển thị form nhập văn bản dài


@app.post("/summarize/background")
def summarize_background(request: Request, background_tasks: BackgroundTasks, document_text: str = Form(...), db: Session = Depends(get_db)):
    text = document_text.strip()                                      # Cắt bỏ khoảng trắng thừa
    if not text: return RedirectResponse(url="/summarize", status_code=303)

    job = create_job(db, input_text=text, mode="background")          # Tạo job trong DB với trạng thái pending
    background_tasks.add_task(run_summary_job, job.id)                # Đưa hàm xử lý vào hàng đợi chạy ngầm của FastAPI
    return RedirectResponse(url=f"/jobs/{job.id}", status_code=303)  # Chuyển ngay người dùng sang trang theo dõi tiến độ


@app.post("/summarize/sync", response_class=HTMLResponse)
def summarize_sync(request: Request, document_text: str = Form(...), db: Session = Depends(get_db)):
    text = document_text.strip()
    if not text: return RedirectResponse(url="/summarize", status_code=303)

    started = time.perf_counter()                                     # Bấm giờ đo độ trễ xử lý đồng bộ
    try:
        result = call_llm_from_text(text)                             # Gọi LLM đồng bộ (chặn luồng xử lý cho đến khi có kết quả)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        save_completed_job(db, text, result, "sync", elapsed_ms)      # Lưu job hoàn thành vào CSDL
        return templates.TemplateResponse("summarize_result.html", {"request": request, "mode": "sync", "result_text": result, "processing_time_ms": elapsed_ms})
    except Exception as e:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        save_completed_job(db, text, "", "sync", elapsed_ms, status="failed", err=str(e))
        return templates.TemplateResponse("summarize_result.html", {"request": request, "mode": "sync", "result_text": f"Lỗi: {e}", "processing_time_ms": elapsed_ms})


@app.post("/summarize/async", response_class=HTMLResponse)
async def summarize_async(request: Request, document_text: str = Form(...), db: Session = Depends(get_db)):
    text = document_text.strip()
    if not text: return RedirectResponse(url="/summarize", status_code=303)

    started = time.perf_counter()                                     # Bấm giờ đo độ trễ xử lý bất đồng bộ
    try:
        result = await call_llm_from_text_async(text)                 # Gọi LLM bất đồng bộ với await (không chặn server)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        save_completed_job(db, text, result, "async", elapsed_ms)     # Lưu job hoàn thành vào CSDL
        return templates.TemplateResponse("summarize_result.html", {"request": request, "mode": "async", "result_text": result, "processing_time_ms": elapsed_ms})
    except Exception as e:
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        save_completed_job(db, text, "", "async", elapsed_ms, status="failed", err=str(e))
        return templates.TemplateResponse("summarize_result.html", {"request": request, "mode": "async", "result_text": f"Lỗi: {e}", "processing_time_ms": elapsed_ms})


@app.get("/jobs/{job_id}", response_class=HTMLResponse)
def job_status(job_id: int, request: Request, db: Session = Depends(get_db)):
    job = db.query(AIJob).filter(AIJob.id == job_id).first()          # Truy vấn trạng thái job theo id
    if not job: return RedirectResponse(url="/jobs", status_code=303)
    return templates.TemplateResponse("job_status.html", {"request": request, "job": job})  # Hiển thị trang theo dõi trạng thái


@app.get("/jobs", response_class=HTMLResponse)
def list_jobs(request: Request, db: Session = Depends(get_db)):
    jobs = db.query(AIJob).order_by(AIJob.id.desc()).all()            # Lấy toàn bộ danh sách jobs đã chạy
    return templates.TemplateResponse("jobs_list.html", {"request": request, "jobs": jobs})  # Hiển thị bảng tổng hợp hiệu năng
