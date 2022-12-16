# aapoonmessenger-userservice

You need to install following things before project setup:

## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install aapoon User Microservice Backend.

```bash
pip install -r requirements.txt
```

## Usage

Run this to make sure your database in sync with latest database changes.
```python
python manage.py migrate
```

Run this to run the server on Port 8000:
```python
python manage.py runserver
```

## Coding Standards:
Make sure you're following the same structure for new apps which is already being used for the existing ones.
Always create an "**api**" folder and add the api's related things there(**viewsets, serializer, routers**).

Make sure you use small functions instead of one messy function or class.