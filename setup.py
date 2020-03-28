#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

try:  # for pip >= 10
    from pip._internal.req import parse_requirements
except ImportError:  # for pip <= 9.0.3
    from pip.req import parse_requirements

try:  # for pip >= 10
    from pip._internal.download import PipSession
except ImportError:  # for pip <= 9.0.3
    from pip.download import PipSession

from glob import glob

import os
import subprocess
import sys

PATH_ROOT = os.path.dirname(os.path.abspath(__file__))

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


def get_version(path_root: str = PATH_ROOT):
    """Obtain the version number"""
    import importlib

    mod = importlib.machinery.SourceFileLoader(
        'version',
        os.path.abspath(
            os.path.join(path_root, 'AlertaDengue', 'ad_main', 'version.py',)
        ),
    ).load_module()
    return mod.__version__


def list_dir(pathname=PATH_ROOT, dir_name=''):
    result = glob(os.path.join(pathname, dir_name, '**'), recursive=True)[1:]

    size = len(pathname)

    return ['.%s' % r[size:] for r in result]


with open(
    os.path.join(PATH_ROOT, 'README.md'), encoding='utf-8'
) as readme_file:
    readme = readme_file.read()

with open(
    os.path.join(PATH_ROOT, 'HISTORY.md'), encoding='utf-8'
) as history_file:
    history = history_file.read()

install_reqs = parse_requirements(
    os.path.join(PATH_ROOT, 'requirements.txt'), session=PipSession()
)

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
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    cmdclass=cmdclass,
    scripts=['AlertaDengue/manage.py'],
    include_package_data=True,
    # test_suite='tests',
    # tests_require=test_requirements
)
