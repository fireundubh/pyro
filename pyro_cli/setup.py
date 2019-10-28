import os
from setuptools import setup

with open(os.path.join(os.path.dirname(__file__), 'README.md'), mode='r') as f:
    long_description = f.read()

version='1.3.3'

setup(
    name='Pyro CLI',
    version=version,
    description='An incremental build system for Skyrim Classic (TESV), Skyrim Special Edition (SSE), and Fallout 4 (FO4) projects',
    long_description=long_description,
    author='fireundubh',
    author_email='fireundubh@gmail.com',
    license='MIT License',
    packages=['pyro_cli'],
    install_requires=['pyro'],
    zip_safe=False,
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)
