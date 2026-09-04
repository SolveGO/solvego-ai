# =========================
# 1. KataGo build
# =========================
FROM debian:bookworm-slim AS katago-builder

RUN apt-get update && apt-get install -y \
    git \
    cmake \
    g++ \
    libzip-dev \
    libeigen3-dev \
    zlib1g-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

RUN git clone --branch v1.18.2 --depth 1 \
    https://github.com/lightvector/KataGo.git

WORKDIR /build/KataGo/cpp

RUN cmake . \
    -DUSE_BACKEND=EIGEN \
    -DUSE_AVX2=1 \
    && make -j2

# =========================
# 2. FastAPI runtime
# =========================
FROM python:3.12-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y \
    libzip4 \
    zlib1g \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

COPY --from=katago-builder \
    /build/KataGo/cpp/katago \
    /usr/local/bin/katago

ENV KATAGO_PATH=/usr/local/bin/katago
ENV KATAGO_CONFIG_PATH=/app/katago/analysis.cfg

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]