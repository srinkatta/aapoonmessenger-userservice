# syntax=docker/dockerfile:1


FROM python:3.8
ENV PYTHONUNBUFFERED=1


# copy source and install dependencies
WORKDIR /code
COPY . /code/
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

RUN python manage.py makemigrations
RUN python manage.py migrate

# start serverd
EXPOSE 8000
#CMD ["gunicorn", "--preload", "--bind", "0.0.0.0:8000", "--keep-alive", "180", "--workers", "3", "--worker-connections", "1000", "aapooncontact.wsgi:application"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--keep-alive", "30", "--workers", "3", "--log-level", "debug", "--access-logfile", "-", "--log-file", "-", "--timeout", "90", "user_service.wsgi:application"]
#CMD ["python", "gcrmserver/bin/manage.py", "runserver", "0.0.0.0:8000"]
