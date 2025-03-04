# Stage 1: Build stage
FROM python:3.9-slim AS builder

WORKDIR /app

# Copy requirements file
COPY requirements.txt .

# Install dependencies in user space
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Final stage
FROM python:3.9-slim

WORKDIR /app

# Copy only the necessary files from the builder stage
COPY --from=builder /root/.local /root/.local
COPY app2.py .
COPY templates ./templates

# Ensure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Expose port 80
EXPOSE 80

# Run the application
CMD ["python", "app2.py"]