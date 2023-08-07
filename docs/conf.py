# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import django

# Set the Django settings module before importing any Django components
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "user_service.settings")

# configure

project = "aapoonmessenger-user"
copyright = "2023, Praveen Gouda"
author = "Praveen Gouda"

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
import os
import sys

sys.path.insert(0, os.path.abspath(".."))
print(sys.path.insert(0, os.path.abspath("..")))

autodoc_mock_imports = [
    "django",
    "drf_spectacular",
    "rest_framework",
    "drf_flex_fields",
    "rest_flex_fields",
]

# Add this line to specify the master document
master_doc = "index"
