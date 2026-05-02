FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# ─── 健康檢查（STANDARDS.md §3.4）────────────────────────────
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8897/health || exit 1

# 註：不使用 --log-config /dev/null（uvicorn 會把 fileConfig 套到空檔案 → RuntimeError）
# uvicorn 的 access log 會與 structlog 並存（可接受，未來如需完全靜默 uvicorn
# 改用 --no-access-log + 自訂 LOGGING_CONFIG dict）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8897"]
