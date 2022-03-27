from setuptools import setup, find_packages

setup(
    name="pocket",
    version="1.0",
    author="Seth Park",
    packages=find_packages(exclude=("test", "examples"))
)

