# Use an official Python runtime as a parent image
FROM python:3.10-slim-buster

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for psycopg2-binary
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     build-essential \
#     libpq-dev \
#     && rm -rf /var/lib/apt/lists/*

# Copy the requirements file into the container
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container
COPY . .

# Expose port 8000 for the Uvicorn server
EXPOSE 8000

# Define environment variables for database connection
# These will be overridden by docker-compose or Kubernetes secrets in production
ENV DATABASE_URL="postgresql://user:password@db:5432/todo_db"

# Command to run the application using Uvicorn
# --host 0.0.0.0 makes the server accessible from outside the container
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]