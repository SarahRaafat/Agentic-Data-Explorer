# Hugging Face Spaces (Docker) — Streamlit Agentic Data Explorer
FROM python:3.11-slim

WORKDIR /app

# Build tools for some Python wheels (pandas, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY shared/requirements.txt shared/requirements.txt
COPY streamlit/requirements.txt streamlit/requirements.txt

RUN pip install --no-cache-dir -r streamlit/requirements.txt

COPY shared/ shared/
COPY streamlit/ streamlit/

# Secrets come from Space Settings (ANTHROPIC_API_KEY); do not bake .env into the image
ENV STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false \
    PYTHONUNBUFFERED=1

EXPOSE 7860

CMD ["streamlit", "run", "streamlit/app.py", \
     "--server.port=7860", \
     "--server.address=0.0.0.0", \
     "--server.fileWatcherType=none"]
