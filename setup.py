#!/usr/bin/env python

from setuptools import setup

setup(
    name='django-xmlrpc-wp',
    version='0.0.1',
    description='Publish content to your Django site using the WordPress mobile app.',
    author='Raymond Butcher',
    author_email='randomy@gmail.com',
    url='https://github.com/apn-online/django-xmlrpc-wp',
    license='MIT',
    packages=(
        'xmlrpc_wp',
    ),
    install_requires=(
        'django',
    ),
)
