#!/usr/bin/env python

from setuptools import setup

setup(name='PySNARK',
      version='0.3.1',
      description='Python zk-SNARK execution environment',
      author='Varun Gandhi',
      author_email='vgandhi@g.harvard.edu',
      url='https://github.com/vargandhi/pysnark',
      packages=['pysnark','pysnark.qaptools','pysnark.libsnark', 'pysnark.zkinterface'],
      package_data={'pysnark.qaptools': ['*.sol']},
      extras_require={
        'libsnark':  ["python-libsnark>=0.3.1"],
      },
)
