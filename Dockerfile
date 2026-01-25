# It uses a "slim" Python image to reduce the attack surface.
FROM python:3.11-slim

# Defines the working directory within the container.
WORKDIR /app

# Installs minimal system dependencies if necessary.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential && \
    rm -rf /var/lib/apt/lists/*

# Copy only the dependency manifest first (optimizes Docker caching).
COPY requirements.txt .

# Installs the technological weapons listed in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the source code into the container.
COPY . .

# Expose the port that FastAPI uses
EXPOSE 8000

# Command to start the API in operational mode
CMD ["uvicorn", "src.infrastructure.api:app", "--host", "0.0.0.0", "--port", "8000"]