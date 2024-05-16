# Use a slim Python 3.9 base image
FROM python:3.11-slim

# Set environment variable for unbuffered output
ENV PYTHONUNBUFFERED 1

# Create a working directory for the application
WORKDIR /app

# Copy requirements.txt and install dependencies
COPY requirements.txt ./
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copy your Django project code
COPY ./app /app

# Expose port 8000 (default for Django development server)
EXPOSE 8000

# Set the command to run migrations, collect static files (if applicable), and start the development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]