FROM python:3.15-slim
WORKDIR /app
COPY server.py .
COPY static ./static
ENV DATA_DIR=/data PYTHONUNBUFFERED=1
EXPOSE 8080
CMD ["python", "server.py"]
