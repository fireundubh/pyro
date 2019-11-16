from setuptools import find_packages, setup

setup(
    name='Pyro',
    description='An incremental build system for Skyrim Classic (TESV), Skyrim Special Edition (SSE), and Fallout 4 (FO4) projects',
    author='fireundubh',
    author_email='fireundubh@gmail.com',
    license='MIT License',
    packages=find_packages(),
    zip_safe=False,
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
)
