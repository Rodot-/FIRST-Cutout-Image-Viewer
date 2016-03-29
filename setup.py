from setuptools import setup, find_packages

setup(
name = 'FCT', 
version = '1.0.5',
description = 'Basic Library for Viewing Radio Images',
url = 'http://github.com/Rodot-/FIRST-Cutout-Image-Viewer',
author = 'John (Jack) T O\'Brien',
author_email = 'john.t.obrien@drexel.edu',
license = 'GNU',
scripts = ['FCT/FIRST_cutouts.py'],
packages = find_packages(),
install_requires = ['astropy>=1.1.1','numpy>=1.6.0','eventlet>=0.18.4','matplotlib>=1.5.1'],
zip_safe = False)


