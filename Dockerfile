# Use a minimal Python 3.11 base image
FROM python:3.10-alpine3.14

# Install necessary development tools
RUN apk add --no-cache build-base linux-headers

# Set environment variable for unbuffered output
ENV PYTHONUNBUFFERED 1

COPY ./requirements.txt /requirements.txt
COPY ./app /app
COPY ./scripts /scripts

# Create a directory for the application code
WORKDIR /app
EXPOSE 8000

# Install system dependencies
RUN python -m venv /py && \
    /py/bin/pip install --upgrade pip && \
    /py/bin/pip install -r /requirements.txt && \
    adduser --disabled-password --no-create-home app && \
    mkdir -p /vol/web/static && \
    chown -R app:app /vol && \
    chmod -R 755 /vol && \
    chmod -R +x /scripts

ENV PATH="/scripts:/py/bin:$PATH"

USER app
    
# Command to run the production server
CMD ["run.sh"]