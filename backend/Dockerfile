FROM python:3.12-slim

WORKDIR /app

# 以非 root 运行；需要写数据卷，先把目录建出来再交给运行用户。
RUN useradd --create-home --shell /usr/sbin/nologin app \
    && mkdir -p /app/data /app/mock

COPY requirements.txt .

# Linux 上直接装 sentence-transformers 会连带拉入 CUDA 版 torch（nvidia-* 依赖数 GB），
# 而这里只需要 CPU 推理，因此先单独装 CPU 版 torch，镜像能从 ~7 GB 降到 ~1.5 GB。
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --retries 10 --timeout 120 --index-url https://download.pytorch.org/whl/cpu torch

# 可选 pip 镜像源：国内网络直连 PyPI 拉 PyTorch 会非常慢，
# compose 里默认传清华源，海外环境可以覆盖或留空走官方源。
ARG PIP_INDEX_URL=
# 用 BuildKit 缓存挂载保存 pip 缓存：网络抖动导致失败时，重跑可续传已下载的 wheel。
RUN --mount=type=cache,target=/root/.cache/pip \
    if [ -n "$PIP_INDEX_URL" ]; then \
        pip install --retries 10 --timeout 120 -i "$PIP_INDEX_URL" -r requirements.txt; \
    else \
        pip install --retries 10 --timeout 120 -r requirements.txt; \
    fi

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
