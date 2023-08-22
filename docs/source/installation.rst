aapoonmessenger-userservice
=============================

Installation
=============

Before setting up the project, you need to install the required dependencies. Use the package manager ``pip`` to install ``aapoonMessenger-user Microservice Backend``.

.. code-block::

        pip install -r requirements.txt

Usage
=====

To synchronize your database with the latest changes, run the following command:

.. code-block::

        python manage.py migrate

To run the server on Port 8000, execute:

.. code-block::

        python manage.py runserver

Coding Standards
================

After successfully running the project, it is recommended to install ``pre-commit`` to prevent committing bugs or issues early on and improve codebase quality.

To install ``pre-commit``, use the following command:

.. code-block::

       pre-commit install

Ensure that you follow the same structure for new apps as the one already being used for the existing ones. Always create an "api" folder and add the API-related components there (viewsets, serializers, routers).

It is advised to use small functions instead of creating one large and messy function or class.

Note
====

This documentation is written using reStructuredText (rst) format, a markup language for technical documentation in Python.
