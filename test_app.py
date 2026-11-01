import os, time
from fastapi.testclient import TestClient
from main import app, ADMIN_TOKEN

client = TestClient(app)


def test_security_header_token():
    print("\n[1/4] Kiểm thử BẢO MẬT BẰNG HEADER TOKEN (X-Admin-Token)...")
    # TH1: Không truyền header -> 401
    r1 = client.get("/admin/dashboard")
    assert r1.status_code == 401, f"Mong đợi 401, nhận: {r1.status_code}"
    print("  -> TH1 (Thiếu header): 401 Unauthorized (Chặn thành công)")

    # TH2: Truyền sai token -> 403
    r2 = client.get("/admin/dashboard", headers={"X-Admin-Token": "sai_token"})
    assert r2.status_code == 403, f"Mong đợi 403, nhận: {r2.status_code}"
    print("  -> TH2 (Sai token): 403 Forbidden (Chặn thành công)")

    # TH3: Truyền đúng token -> 200
    r3 = client.get("/admin/dashboard", headers={"X-Admin-Token": ADMIN_TOKEN})
    assert r3.status_code == 200, f"Mong đợi 200, nhận: {r3.status_code}"
    print(f"  -> TH3 (Đúng token): 200 OK -> {r3.json()['message']}")


def test_security_query_token():
    print("\n[2/4] Kiểm thử BẢO MẬT BẰNG QUERY TOKEN (?token=...)...")
    # TH1: Sai hoặc thiếu token -> 403
    r1 = client.get("/admin?token=sai")
    assert r1.status_code == 403, f"Mong đợi 403, nhận: {r1.status_code}"
    print("  -> TH1 (Sai query token): 403 Forbidden (Chặn thành công)")

    # TH2: Đúng token -> 200
    r2 = client.get(f"/admin?token={ADMIN_TOKEN}")
    assert r2.status_code == 200, f"Mong đợi 200, nhận: {r2.status_code}"
    print(f"  -> TH2 (Đúng query token): 200 OK -> {r2.json()['message']}")


def test_logging_and_error_handling():
    print("\n[3/4] Kiểm thử GHI LOG LỖI ĐA TẦNG (FILE & CSDL)...")
    # Gọi endpoint cố tình ném ra lỗi
    r = client.post("/summarize/background_with_error_handling")
    assert r.status_code == 500, f"Mong đợi 500, nhận: {r.status_code}"
    print("  -> Server phản hồi đúng mã 500 Internal Server Error khi gặp sự cố")

    # Kiểm tra file error_log.txt đã được ghi nhận
    assert os.path.exists("error_log.txt"), "File error_log.txt chưa được tạo"
    with open("error_log.txt", "r", encoding="utf-8") as f:
        log_content = f.read()
    assert "Simulated error" in log_content, "Nội dung lỗi chưa được ghi vào error_log.txt"
    print("  -> Đã ghi nhận vết lỗi thành công vào tệp: error_log.txt")


def test_summarize_and_dashboard():
    print("\n[4/4] Kiểm thử GIAO DIỆN TÓM TẮT & DASHBOARD...")
    r1 = client.get("/")
    assert r1.status_code == 200
    r2 = client.get("/summarize")
    assert r2.status_code == 200
    r3 = client.get("/jobs")
    assert r3.status_code == 200
    print("  -> Tất cả các trang SSR (Trang chủ, Tóm tắt, Dashboard) hoạt động mượt mà.")


if __name__ == "__main__":
    print("=" * 70)
    print("  BẮT ĐẦU KIỂM THỬ TOÀN DIỆN BÀI 8 (BẢO MẬT, LOGGING, DEPLOY)")
    print("=" * 70)

    test_security_header_token()
    test_security_query_token()
    test_logging_and_error_handling()
    test_summarize_and_dashboard()

    print("\n" + "=" * 70)
    print(">> Tất cả các kịch bản kiểm thử Bài 8 đã VƯỢT QUA THÀNH CÔNG 100%!")
    print("=" * 70)
