FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
COPY model/ ./model/

ENV PYTHONUNBUFFERED=1

CMD ["python", "-m", "app.udf_entry"]