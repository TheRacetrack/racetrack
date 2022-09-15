import setuptools

setuptools.setup(
    name="plugin_bundler",
    version='0.0.1',
    author='ERST',
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8.0',
    install_requires=[],
    entry_points={
        "console_scripts": [
            "racetrack-plugin-bundler = plugin_bundler.main:main",
        ],
    },
)
