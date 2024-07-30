FROM python:3.9

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set the working directory inside the container
WORKDIR /code

# Copy the requirements file
COPY requirements.txt /code/

# Install dependencies
RUN pip install -r requirements.txt

# Copy the entire project
COPY . /code/

# Start the Django development server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]