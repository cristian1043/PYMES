FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5002

ENV FLASK_ENV=production
ENV PORT=5002

CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5002", "src.app:app"]
