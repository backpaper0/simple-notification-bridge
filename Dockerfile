FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./
RUN pip install uv && \
    uv pip install --system -r pyproject.toml

COPY . .

CMD ["python", "main.py"]