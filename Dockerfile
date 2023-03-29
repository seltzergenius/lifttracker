# Use the official Python image as the base image
FROM python:3.8-slim

# Set the working directory
WORKDIR /app

# Copy the requirements.txt file into the container
COPY requirements.txt .

# Install dev headers/libs for mysql
RUN apt-get update && apt-get install -y build-essential libmariadb-dev default-libmysqlclient-dev

# Install the required packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application's source code
COPY . .

# Expose the Gunicorn port
EXPOSE 8000

# Start Gunicorn to serve the application
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:8000", "app:app"]
