# Copyright (c) 2017  Niklas Rosenstein
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import os
import sys
from setuptools import setup
from os import system, path
from codecs import open

def readme():
  """
  This helper function uses the `pandoc` command to convert the `README.md`
  into a `README.rst` file, because we need the long_description in ReST
  format. This function will only generate the `README.rst` if any of the
  `setup dist...` commands are used, otherwise it will return an empty string
  or return the content of the already existing `README.rst` file.
  """

  if os.path.isfile('README.md') and any('dist' in x for x in sys.argv[1:]):
    if os.system('pandoc -s README.md -o README.rst') != 0:
      print('-----------------------------------------------------------------')
      print('WARNING: README.rst could not be generated, pandoc command failed')
      print('-----------------------------------------------------------------')
      if sys.stdout.isatty():
        input("Enter to continue... ")
    else:
      print("Generated README.rst with Pandoc")

  if os.path.isfile('README.rst'):
    with open('README.rst') as fp:
      return fp.read()
  return ''

setup(
  name='nocrux',
  version='2.0.2',
  description='a painless per-user daemon manager',
  long_description=readme(),
  author='Niklas Rosenstein',
  author_email='rosensteinniklas@gmail.com',
  url='https://github.com/NiklasRosenstein/nocrux',
  py_modules=['nocrux'],
  install_requires=['nr>=1.4.6'],
  entry_points=dict(
    console_scripts=[
      'nocrux=nocrux:main'
    ]
  ),
)
