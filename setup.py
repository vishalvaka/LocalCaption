#!/usr/bin/env python3
"""
Setup script for LocalCaption
"""

from setuptools import setup, find_packages
import os

# Read the README file
def read_readme():
    with open("README.md", "r", encoding="utf-8") as fh:
        return fh.read()

# Read requirements
def read_requirements():
    with open("requirements.txt", "r", encoding="utf-8") as fh:
        return [line.strip() for line in fh if line.strip() and not line.startswith("#")]

setup(
    name="localcaption",
    version="1.0.0",
    author="LocalCaption Team",
    author_email="",
    description="Live captions for any audio using local ASR",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/localcaption",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Sound/Audio :: Capture/Recording",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
    ],
    python_requires=">=3.8",
    install_requires=read_requirements(),
    entry_points={
        "console_scripts": [
            "localcaption=localcaption.main:main",
        ],
    },
    include_package_data=True,
    package_data={
        "localcaption": ["*.yaml", "*.yml"],
    },
    keywords="speech recognition, captions, accessibility, real-time, local, offline",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/localcaption/issues",
        "Source": "https://github.com/yourusername/localcaption",
        "Documentation": "https://github.com/yourusername/localcaption#readme",
    },
)
