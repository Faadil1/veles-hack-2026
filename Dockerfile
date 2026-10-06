FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    IDE_BACKEND_URL=http://host.docker.internal:3001/api \
    PORT=8000
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY steward ./steward
RUN useradd --create-home --uid 10001 steward
USER steward
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8000/health'); sys.exit(0)"
CMD ["python", "-m", "steward.app"]
