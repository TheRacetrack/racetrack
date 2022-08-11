import setuptools
from racetrack_client import __version__

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt", "r") as fh:
    install_requires = fh.read().splitlines()

setuptools.setup(
    name="racetrack-client",
    version=__version__,
    author='ERST',
    author_email="noreply@erst.dk",
    description="CLI client tool for deploying workloads to Racetrack",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/TheRacetrack/racetrack",
    packages=setuptools.find_packages(exclude=["tests.*", "tests", "plugins"]),
    classifiers=[
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Intended Audience :: Information Technology',
    ],
    python_requires='>=3.8.0',
    install_requires=install_requires,
    dependency_links=[],
    license='GPLv3+',
    entry_points={
        "console_scripts": [
            "racetrack = racetrack_client.main:main",
        ],
    },
)
