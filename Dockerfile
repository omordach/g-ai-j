FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure Python can import the package from ./src
ENV PYTHONPATH=/app/src

EXPOSE 8080

CMD ["gunicorn","-w","2","-k","gthread","-b","0.0.0.0:8080","gaij.app:app"]
