FROM python:3.12-slim

WORKDIR /app

# 以非 root 运行；需要写数据卷，先把目录建出来再交给运行用户。
RUN useradd --create-home --shell /usr/sbin/nologin app \
    && mkdir -p /app/data /app/mock

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY evaluation ./evaluation
COPY mock ./mock
COPY pytest.ini .

RUN chown -R app:app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
