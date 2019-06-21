from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open('requirements.txt') as f:
    requirements = f.read().splitlines()
       
setup(
    name='Classifier',
    description='Classify mri modality',
    url='https://github.com/bsauty/sc_mri_dl_classifier',
    author='NeuroPoly',
    author_email='none@none.com',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Programming Language :: Python :: 3',
    ],
    packages=find_packages(exclude=['docs', 'tests']),
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'train_classifier=classifier.main:run_main',
            'classify_acquisition=classifier.classify:run_main',
        ],
    },
)

