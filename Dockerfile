# Use Python 3.11 slim as base image
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# token.json is not committed. Mount it at runtime:
#   docker run -v /path/to/token.json:/app/token.json <image>
# Or include it in the image by uncommenting the line below:
# COPY token.json /app/token.json

CMD ["python", "main.py"]
