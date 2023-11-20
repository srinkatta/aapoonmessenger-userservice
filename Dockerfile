# syntax=docker/dockerfile:1


FROM python:3.11
ENV PYTHONUNBUFFERED=1


# copy source and install dependencies
WORKDIR /code
COPY . /code/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
#RUN pre-commit install

# Create and copy the entrypoint script
COPY entrypoint.sh /app
RUN chmod +x /app/entrypoint.sh

# Apply database migrations
#RUN python manage.py makemigrations
RUN python manage.py migrate

# Set the entrypoint to the entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]

# RUN python manage.py makemigrations
# RUN python manage.py migrate
#CMD ["python", "manage.py", "migrate"]

# start serverd
EXPOSE 8000
#CMD ["gunicorn", "--preload", "--bind", "0.0.0.0:8000", "--keep-alive", "180", "--workers", "3", "--worker-connections", "1000", "aapooncontact.wsgi:application"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--forwarded-allow-ips", "*", "--keep-alive", "30", "--workers", "3", "--log-level", "debug", "--access-logfile", "-", "--log-file", "-", "--timeout", "180",  "--statsd-host", "3.110.84.221:9125", "--statsd-prefix","aapoonmessenger.userservice", "user_service.wsgi:application"]
#CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
