"""
Setup script.
"""

from setuptools import setup

setup(
    name="axpert-interface",
    version="0.2.1",
    py_modules=["axpert", "entities", "lib"],
    install_requires=[
        "click>=8.1.7",
        "crcmod>=1.7",
        "prettytable>=3.10.0",
        "paho-mqtt>=2.0.0",
    ],
    entry_points={
        "console_scripts": [
            "axpert = axpert:cli",
        ],
    },
)
