from setuptools import find_packages, setup

setup(
    name='Pyro',
    description='A parallelized incremental build system for TESV, SSE, and FO4 projects',
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
