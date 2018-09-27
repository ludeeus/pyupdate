"""Setup configuration."""
import setuptools

setuptools.setup(
    name="pyupdate",
    version='0.0.0',
    author="Joakim Sorensen",
    author_email="ludeeus@gmail.com",
    description="A python module update stuff.",
    long_description="A python module update stuff.",
    install_requires=['requests'],
    long_description_content_type="text/markdown",
    url="https://github.com/ludeeus/pyupdate",
    packages=setuptools.find_packages(),
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
)
