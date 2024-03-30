'''
Created on Oct 4, 2020

@author: esdev
'''
from setuptools import setup, find_packages

setup(name='slacm',
      version='0.0.1',
      description='Simple Light-weight Actor Model',
      url='',
      author='slacm',
      author_email='gabor.karsai@vanderbilt.edu',
      license='',
      packages=find_packages(),
      package_data = {
          "" : ["*.tx"]
          },
      scripts = [
        "slacm_run",
        "slacm_fab"
     ],
    zip_safe=False)