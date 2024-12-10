FROM python:3.11

# Instala dependencias necesarias para compilar SQLCipher
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
# Añadir dependencias del sistema
RUN apt-get update && apt-get install -y libsqlite3-dev
# # Descarga e instala SQLCipher 4.6.1
# RUN wget https://github.com/sqlcipher/sqlcipher/archive/refs/tags/v4.6.1.tar.gz && \
#     tar -xvzf v4.6.1.tar.gz && \
#     cd sqlcipher-4.6.1 && \
#     ./configure --enable-tempstore=yes CFLAGS="-DSQLITE_HAS_CODEC" LDFLAGS="-lcrypto" && \
#     make && make install && \
#     cd .. && rm -rf sqlcipher-4.6.1 v4.6.1.tar.gz

# Establece el path para que las librerías de SQLCipher sean accesibles
ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

# Setea variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Define el directorio de trabajo
WORKDIR /code

# Copia el archivo de requerimientos y las dependencias de Python
COPY requirements.txt /code/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Copia el código del proyecto
COPY . /code/

# Expone el puerto donde corre la app
EXPOSE 8000