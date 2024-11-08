from setuptools import setup, find_packages

setup(
    name='StingrayExplorer',
    version='0.1',
    packages=find_packages(include=['modules', 'modules.*']),
    install_requires=[
        'sphinx',
        'sphinx-rtd-theme',
        'sphinx-autodoc-typehints',
        'stingray',
        # Add other dependencies here if needed
    ],
)
