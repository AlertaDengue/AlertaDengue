from setuptools import setup, find_packages
import os
import subprocess
import sys
import site


site.ENABLE_USER_SITE = "--user" in sys.argv[1:]

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


with open(
    os.path.join(PATH_ROOT, 'README.md'), encoding='utf-8'
) as readme_file:
    readme = readme_file.read()

with open(
    os.path.join(PATH_ROOT, 'HISTORY.md'), encoding='utf-8'
) as history_file:
    history = history_file.read()


def read(filename):
    return [req.strip() for req in open(filename).readlines()]


setup(
    name='AlertaDengue',
    version='2.5.0',
    description="Dengue alert",
    long_description=readme + '\n\n' + history,
    author="FIOCRUZ",
    author_email='alerta_dengue@fiocruz.br',
    url='https://github.com/AlertaDengue/AlertaDengue',
    packages=find_packages("AlertaDengue"),
    install_requires=read("requirements.txt"),
    extras_require={"dev": read("requirements-dev.txt")},
    license="GNU General Public License v3",
    zip_safe=False,
    keywords='dengue',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
    ],
    cmdclass=cmdclass,
    scripts=['AlertaDengue/manage.py'],
    include_package_data=True,
    package_dir={
        "": "AlertaDengue"
    },  # tell distutils packages are under AlertaDengue
    # test_suite='tests',
    # tests_require=test_requirements
)
