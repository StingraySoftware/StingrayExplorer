# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys
sys.path.insert(0, os.path.abspath('../../'))

project = 'Stingray Explorer'
copyright = '2024, Kartik Mandar'
author = 'Kartik Mandar'
release = '0.1'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',           # Main extension for auto-documentation
    'sphinx.ext.napoleon',          # Supports Google/NumPy style docstrings
    'sphinx.ext.autosummary',       # Generates summary tables for modules/classes
    'sphinx.ext.viewcode',          # Adds links to highlighted source code
    'sphinx.ext.intersphinx',       # Links to documentation of external libraries
]

autosummary_generate = True      # Enables automatic summary generation

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'scipy': ('https://docs.scipy.org/doc/scipy/', None),
}

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
