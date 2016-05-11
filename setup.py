# Copyright (c) 2016  Niklas Rosenstein
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

from setuptools import setup
from os import system, path
from codecs import open

if path.isfile('README.md'):
  assert 0 == system('pandoc -s README.md -o README.rst')

with open('README.rst', encoding='utf8') as fp:
  long_description = fp.read()

setup(
  name='nocrux',
  version='1.1.1',
  description='painless per-user daemon manager',
  long_description=long_description,
  author='Niklas Rosenstein',
  author_email='rosensteinniklas@gmail.com',
  url='https://github.com/NiklasRosenstein/nocrux',
  modules=['nocrux'],
  entry_points=dict(
    console_scripts=[
      'nocrux=nocrux:main'
    ]
  ),
)
