# Use a slim Python 3.11 base image
FROM python:3.11-slim

# Set environment variable for unbuffered output
ENV PYTHONUNBUFFERED=1

# Create a working directory for the application
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY requirements.txt ./
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy your Django project code
COPY ./app /app

# Expose port 8080, which is the default port for Cloud Run
EXPOSE 8080

# Use Gunicorn to serve the Django application
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "e_commerce_api.wsgi:application"]
