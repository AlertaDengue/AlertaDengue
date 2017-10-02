#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, Command, find_packages
from pip.req import parse_requirements
from pip.download import PipSession
from glob import glob

import os
import sys

PATH_ROOT = os.getcwd()


# Documentation building command
try:
    from sphinx.setup_command import BuildDoc as SphinxBuildDoc

    class BuildDoc(SphinxBuildDoc):
        """Run in-place build before Sphinx doc build"""
        def run(self):
            ret = subprocess.call(
                [sys.executable, sys.argv[0], 'build_ext', '-i']
            )
            if ret != 0:
                raise RuntimeError("Building Scipy failed!")
            SphinxBuildDoc.run(self)
    cmdclass = {'build_sphinx': BuildDoc}
except ImportError:
    cmdclass = {}


def get_version():
    """Obtain the version number"""
    import imp
    mod = imp.load_source(
        'version', os.path.join('AlertaDengue', 'version.py')
    )
    return mod.__version__


def list_dir(pathname=PATH_ROOT, dir_name=''):
    result = glob(
        os.path.join(pathname, dir_name, '**'), 
        recursive=True
    )[1:]

    size = len(pathname)

    return ['.%s' % r[size:] for r in result]

with open('../README.md') as readme_file:
    readme = readme_file.read()

with open('../HISTORY.md') as history_file:
    history = history_file.read()

install_reqs = parse_requirements('requirements.txt', session=PipSession())

requirements = [str(ir.req) for ir in install_reqs]

test_requirements = [
    # TODO: put package test requirements here
]

setup(
    name='AlertaDengue',
    version=get_version(),
    description="Dengue alert",
    long_description=readme + '\n\n' + history,
    author="FIOCRUZ",
    author_email='alerta_dengue@fiocruz.br',
    url='https://github.com/AlertaDengue/AlertaDengue',
    packages=find_packages(),
    install_requires=requirements,
    license="GNU General Public License v3",
    zip_safe=False,
    keywords='dengue',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    cmdclass=cmdclass,
    # test_suite='tests',
    # tests_require=test_requirements
)
