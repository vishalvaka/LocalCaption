from setuptools import setup, find_packages

setup(
    name="localcaption",
    version="0.1.0",
    description="Live captions for any audio playing on your computer",
    author="LocalCaption Team",
    packages=find_packages(),
    install_requires=[
        "sherpa-onnx>=1.10.0",
        "sounddevice>=0.4.6",
        "PyQt6>=6.6.0",
        "numpy>=1.24.0",
        "psutil>=5.9.0",
        "pyinstaller>=6.0.0",
    ],
    entry_points={
        "console_scripts": [
            "localcaption=localcaption.main:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
)
