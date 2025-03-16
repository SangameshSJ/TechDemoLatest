FROM python:3.9-slim AS builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


FROM python:3.9-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY app1.py .
COPY templates ./templates
ENV PATH=/root/.local/bin:$PATH
EXPOSE 80
CMD ["python", "app1.py"]