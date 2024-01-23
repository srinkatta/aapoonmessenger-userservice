# Multiple Schema Management in PostgreSQL with Django

## Overview

This documentation guides you through the process of maintaining multiple schemas within a single PostgreSQL database using Django. This setup is particularly useful when dealing with a microservices architecture where each microservice requires its own schema within the shared database.

## Prerequisites

Before starting, ensure that you have:

1. PostgreSQL installed.
2. A PostgreSQL database created.
3. Necessary database credentials (username, password, host, etc.).

## Steps

### 1. Database Creation

Create a PostgreSQL database using your preferred method. This can be done through the PostgreSQL command line or a GUI tool.

### 2. Schema Creation

For our use case, let's consider two microservices: one for the circle service and another for the user microservice. You need to create a schema for each microservice within the database.

Use the following SQL commands to create schemas (replace `circle_schema` and `user_schema` with your desired schema names):

```sql
CREATE SCHEMA circle;
CREATE SCHEMA user;
```

### 3. Django Configuration

In each Django microservice, update the database configuration to include the schema information. This involves setting the `DB_SCHEMA_NAME` environment variable.

#### Example Configuration in Django Settings

```python
# settings.py

import os

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'your_database_name',
        'USER': 'your_database_user',
        'PASSWORD': 'your_database_password',
        'HOST': 'your_database_host',
        'PORT': 'your_database_port',
        'OPTIONS': {
            'options': f'-c search_path={os.environ.get("DB_SCHEMA_NAME", "public")}',
        },
    }
}
```

### 4. Environment Variable Setup

In each microservice, set the `DB_SCHEMA_NAME` environment variable to specify the schema you want to use.

#### Example for Circle Service

```bash
export DB_SCHEMA_NAME=circle_schema
```
or just update the value in .env file
```bash
DB_SCHEMA_NAME=circle
```

#### Example for User Microservice

```bash
export DB_SCHEMA_NAME=user_schema
```
or just update the value in .env file
```bash
DB_SCHEMA_NAME=user
```

### 5. Run the Microservices

With the database configured and the environment variables set, run each microservice. They will now interact with their respective schemas within the shared PostgreSQL database.

## Conclusion

This setup allows you to maintain multiple schemas within a single PostgreSQL database, providing a clean and organized approach to managing data for different microservices. Ensure that each microservice is configured with the correct schema name using the `DB_SCHEMA_NAME` environment variable.
