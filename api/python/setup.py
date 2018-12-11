import os
import sys

from setuptools import setup, find_packages
from setuptools.command.install import install

VERSION = "0.0.1"

def readme():
    readme_short = """
    """
    return readme_short

class VerifyVersionCommand(install):
    """Custom command to verify that the git tag matches our version"""
    description = 'verify that the git tag matches our version'

    def run(self):
        tag = os.getenv('CIRCLE_TAG')

        if tag != VERSION:
            info = "Git tag: {0} does not match the version of this app: {1}".format(
                tag, VERSION
            )
            sys.exit(info)

setup(
    name="t4",
    version="0.0.2-dev",
    packages=find_packages(),
    description='T4',
    long_description=readme(),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    author='quiltdata',
    author_email='contact@quiltdata.io',
    license='LICENSE',
    url='https://github.com/quiltdata/quilt-new',
    keywords='',
    install_requires=[
        'appdirs>=1.4.0',
        'aws-requests-auth>=0.4.2',
        'boto3',
        'elasticsearch~=6.3.1',
        'enum34; python_version<"3.0"',     # stdlib backport
        'future>=0.16.0',                   # stdlib backport: 'from builtins import xxx', plus others.
        'jsonlines==1.2.0',
        'numpy>=1.14.0',                    # required by pandas, but missing from its dependencies.
        'packaging>=16.8',
        'pandas>=0.19.2',
        'pathlib2; python_version<="3.5"',  # stdlib backport
        'pyarrow>=0.9.0',
        'requests>=2.12.4',
        'ruamel.yaml<=0.15.70',
        'six>=1.10.0',
        'tqdm>=4.26.0',
        'xattr>=0.9.6; platform_system!="Windows"',
    ],
    extras_require={
        'tests': [
            'codecov',
            'mock',   # XXX correct syntax for extras_require?
            'pytest',
            'pytest-cov',
            'responses',
            'tox',
            'detox',
            'tox-pytest-summary',
        ],
    },
    include_package_data=True,
    entry_points={
        # 'console_scripts': ['quilt=quilt.tools.main:main'],
    },
    cmdclass={
        'verify': VerifyVersionCommand,
    }    
)