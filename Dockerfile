# syntax=docker/dockerfile:1
FROM dtcooper/raspberrypi-os:bookworm

LABEL maintainer="signag"

RUN apt update && apt -y upgrade

RUN apt update && apt install -y \
    gcc-aarch64-linux-gnu \
    python3 \
    python3-dev \
    python3-pip \
    python3-venv \
    python3-opencv \
    python3-gpiozero \
    python3-lgpio \
    ffmpeg \
    python3-picamera2 --no-install-recommends


RUN ln -s /usr/bin/python3 /usr/bin/python

# Prevents Python from writing pyc files.
ENV PYTHONDONTWRITEBYTECODE=1

# Keeps Python from buffering stdout and stderr to avoid situations where
# the application crashes without emitting any logs due to buffering.
ENV PYTHONUNBUFFERED=1

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Copy the source code into the container.
COPY . .

# Install Python dependencies in virtual environment
RUN python -m venv --system-site-packages .venv
ENV PATH=".venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt

# Expose the port that the application listens on.
EXPOSE 5000

# Initialize database for Flask
RUN flask --app raspiCamSrv init-db

# Run the application.
CMD flask --app raspiCamSrv run --port 5000 --host=0.0.0.0