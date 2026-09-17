FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY apps/api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt

COPY packages/contracts/src /app/packages/contracts/src
COPY apps/api/src /app/apps/api/src

ENV PYTHONPATH=/app/apps/api/src:/app/packages/contracts/src

EXPOSE 8000

CMD ["uvicorn", "safewatch_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
