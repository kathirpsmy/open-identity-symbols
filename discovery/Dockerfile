FROM python:3.11-slim

WORKDIR /app

# Install deps
COPY discovery/requirements.txt ./discovery/requirements.txt
RUN pip install --no-cache-dir -r discovery/requirements.txt

# Copy the whole repo so discovery/ can import from backend/data/
COPY . .

ENV PYTHONPATH=/app

CMD ["uvicorn", "discovery.main:app", "--host", "0.0.0.0", "--port", "8001"]
