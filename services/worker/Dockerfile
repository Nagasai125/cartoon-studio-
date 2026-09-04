FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN addgroup --system studio && adduser --system --ingroup studio studio

COPY pyproject.toml README.md ./
COPY packages/pipeline packages/pipeline
RUN pip install --no-cache-dir .

USER studio

CMD ["python", "-m", "cartoon_studio.worker.main"]
