FROM python:3.11-slim as base

ENV PYTHONUNBUFFERED=1
WORKDIR /app

FROM base as builder
COPY requirements.txt /app/
RUN python -m pip install --upgrade pip && \
	pip install --no-cache-dir -r requirements.txt

FROM base as runtime
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY . /app

USER root
CMD ["python", "-m", "src.pipeline"]
