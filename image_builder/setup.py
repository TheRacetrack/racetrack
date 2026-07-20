import setuptools

with open("requirements.txt", "r") as fh:
    install_requires = fh.read().splitlines()

setuptools.setup(
    name="image_builder",
    version='0.0.1',
    author='ERST',
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8.0',
    install_requires=install_requires,
    entry_points={
        "console_scripts": [
            "image_builder = image_builder.main:main",
        ],
    },
)
