# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys
import django

# Set the Django settings module before importing any Django components
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "user_service.settings")

# configure

project = "aapoon user service"
copyright = "2023, aapoon Inc"
author = "Ali Khan & Praveen Gouda"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx_autodoc_typehints",
]

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]


# Set the path to your Django project's source code and modules
sys.path.insert(0, os.path.abspath(".."))

autodoc_mock_imports = [
    "django",
    "allauth",
    "drf_spectacular",
    "rest_framework",
    "drf_flex_fields",
    "rest_flex_fields",
    "rest_framework_api_key",
    "rest_framework_simplejwt",
    "multiselectfield",
    "user.models",
    "user.user_delete",
]

# Add this line to specify the master document
master_doc = "index"
