import os
from setuptools import find_packages, setup
from pip.req import parse_requirements

# allow setup.py to be run from any path
os.chdir(os.path.normpath(os.path.join(os.path.abspath(__file__), os.pardir)))

with open(os.path.join(os.path.dirname(__file__), 'README.md')) as readme:
    README = readme.read()

# parse_requirements() returns generator of pip.req.InstallRequirement objects
install_reqs = parse_requirements(os.path.join(os.path.dirname(__file__), 'requirements.txt'), session=False)

# reqs is a list of requirement
# e.g. ['django==1.5.1', 'mezzanine==1.4.6']
reqs = [str(ir.req) for ir in install_reqs]

setup(
    name='MagiCircles',
    version='1.0',
    packages=find_packages(),
    include_package_data=True,
    author=u'Deby Lepage',
    author_email='db0company@gmail.com',
    url='https://github.com/SchoolIdolTomodachi/MagiCircles',
    license='Simple non code license (SNCL), see LICENCE',
    description='Let\'s do some magic!',
    long_description=README,
    zip_safe=False,
    install_requires = reqs,
)
