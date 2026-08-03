# ─── Imagen base con Node 20 + Python 3 ────────────────────────────────────────
FROM node:20-slim

# Instalar Python 3, pip y dependencias de sistema necesarias para OpenCV
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 \
    python3-pip \
    python3-venv \
    libglib2.0-0 \
    libgl1 \
    libgomp1 \
    libsm6 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# Asegurar que 'python3' esté disponible siempre como binario y limitar hilos para ahorrar RAM
ENV PYTHON_BIN=python3 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1 \
    MKL_NUM_THREADS=1

WORKDIR /app

# ─── Dependencias Python ──────────────────────────────────────────────────
COPY scripts/requirements.txt ./scripts/requirements.txt
RUN pip3 install --no-cache-dir --break-system-packages -r scripts/requirements.txt

# Verificar que OpenCV importa correctamente
RUN python3 -c "import cv2, numpy; print('OpenCV', cv2.__version__, '- OK')"

# ─── Dependencias Node ─────────────────────────────────────────────────────────────
COPY package*.json ./
RUN npm ci --omit=dev

# ─── Código fuente ───────────────────────────────────────────────────────────────
COPY . .

EXPOSE 3000

CMD ["node", "src/index.js"]
