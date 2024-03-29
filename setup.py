"""
Setup script.
"""

from setuptools import setup

setup(
    name="axpert-interface",
    version="0.1.0",
    py_modules=["axpert", "entities"],
    install_requires=["click>=8.1.7", "crcmod>=1.7", "prettytable>=3.10.0"],
    entry_points={
        "console_scripts": [
            "axpert = axpert:cli",
        ],
    },
)
