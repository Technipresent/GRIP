FROM python:3.12-slim
WORKDIR /app
COPY checker_service/requirements.txt .
RUN pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu -r requirements.txt
COPY checker_service ./checker_service
CMD ["sh", "-c", "uvicorn checker_service.app:build_app --factory --host 0.0.0.0 --port ${PORT:-8080}"]
