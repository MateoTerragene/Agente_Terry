FROM python:3.11

RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    pkg-config \
    libssl-dev \
    libsqlite3-dev \
    ffmpeg \
    libdmtx0b \
    libdmtx-dev && \
    rm -rf /var/lib/apt/lists/*

RUN apt-get update && apt-get install -y libsqlite3-dev

ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /code

COPY requirements.txt /code/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

COPY . /code/

EXPOSE 8000