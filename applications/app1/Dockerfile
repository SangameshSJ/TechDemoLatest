FROM python:3.9-slim

WORKDIR /app

COPY app1.py requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 80

CMD ["python", "app1.py"]