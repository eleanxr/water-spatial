#! /usr/bin/env python

from setuptools import setup

requirements = [
    'setuptools',
    # Choose numpy for ArcGIS 10.2
    # 'numpy==1.7.1',
    # Choose pandas for numpy 1.7.1
    # 'pandas==0.13.1',
    'dbfread==2.0.4',
    'xlrd==0.9.3',
    'openpyxl==1.8.6',
]

setup(
    name='watertool',
    version='0.1',
    description='Water data analysis kit.',
    author='Will Dicharry',
    author_email='wdicharry@gmail.com',
    install_requires=requirements,
    packages=['watertool'],
    # test_suite="tests"
)
