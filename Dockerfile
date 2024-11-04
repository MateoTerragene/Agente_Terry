FROM python:3.11

# # Instala ffmpeg
# RUN apt-get update && apt-get install -y ffmpeg

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

COPY requirements.txt /code/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Install FFmpeg and libdmtx libraries
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libdmtx0b \
    libdmtx-dev && \
    rm -rf /var/lib/apt/lists/*
# Copy the entire project
COPY . /code/

# Expose the port the app runs on
EXPOSE 8000
