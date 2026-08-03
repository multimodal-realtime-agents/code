FROM python:3.10-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV AGENT_SYSTEM_SERVICE=backend

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent_system ./agent_system
COPY static ./static

EXPOSE 8080

CMD ["python", "-m", "agent_system.service_entrypoint"]
