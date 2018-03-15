from setuptools import setup, find_packages  # Always prefer setuptools over distutils
from codecs import open  # To use a consistent encoding
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the relevant file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='pybofh',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version='0.2.1',

    description='A Linux system administration automation toolset',
    long_description=long_description,

    # The project's main homepage.
    url='https://github.com/goncalopp/pybofh',

    # Author details
    author='Goncalo Pinheira',
    author_email='goncalopp+pybofh@quorumverita.com',

    # Choose your license
    license='BSD',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: System Administrators',
        'Topic :: System :: Systems Administration',
        'Topic :: System :: Clustering',
        'Topic :: System :: Filesystems',
        'Topic :: System :: Monitoring',
        'License :: OSI Approved :: BSD License',
        'Operating System :: POSIX :: Linux',

        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
    ],

    keywords='linux sysadmin library toolset',

    packages=find_packages(exclude=['contrib', 'docs', 'tests*']),
    setup_requires=['nose', 'mock'],
    test_suite='nose.collector'

)
