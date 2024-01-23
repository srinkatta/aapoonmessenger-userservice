# aapoon User Microservice

## Overview

The aapoon User Microservice is a Django-based application developed in Python 3.11.

## Prerequisites

Before you start, make sure you have the following prerequisites installed:

- Python 3.11 or 3.12 (install directly or use [pyenv](https://github.com/pyenv/pyenv))
- [pip](https://pip.pypa.io/en/stable/) (Python package installer)
- [Pre-commit](https://pre-commit.com/) (optional for developers)

## Getting Started

Follow these steps to set up and run the project:

1. **Clone the Repository:**

    ```bash
    git clone https://github.com/aapoonInc/aapoonmessenger-userservice.git
    cd aapoonmessenger-userservice
    ```

2. **Install Dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

3. **Copy Environment Variables:**

    ```bash
    cp .env.example .env
    ```

4. **Update Environment Variables:**

    Edit the `.env` file and update the values according to your configuration.

5. **Run the Development Server:**

    ```bash
    python manage.py runserver
    ```

    The application will be accessible at [http://localhost:8000/](http://localhost:8000/). View the Swagger docs at [http://127.0.0.1:8000/api/users/schema/swagger-ui/](http://127.0.0.1:8000/api/users/schema/swagger-ui/)

## Developer Setup and Coding Standards

If you're a developer contributing to this project, follow these guidelines to ensure a consistent and high-quality codebase.

1. **Install Pre-commit:**

    ```bash
    pre-commit install
    ```

2. **Run Pre-commit on Every Commit:**

    With pre-commit installed, it will automatically run checks on your code every time you make a commit.

3. **Coding Standards:**

   Ensure you follow the same structure for new apps, creating an "api" folder and organizing API-related components (viewsets, serializers, routers) within it.

   Always prefer small functions over one messy function or class for improved code readability and maintainability.

## Authors/Developers

- Ali Khan ([GitHub](https://github.com/alikhan126), [aapoon GitHub](https://github.com/aliaapoon))
- Praveen Gouda ([GitHub](https://github.com/praveengouda007))
