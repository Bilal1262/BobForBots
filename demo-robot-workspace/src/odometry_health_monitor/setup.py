import os
from glob import glob

from setuptools import find_packages, setup

package_name = "odometry_health_monitor"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(exclude=["test"]),
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        ("share/" + package_name, ["package.xml"]),
        (os.path.join("share", package_name, "launch"), glob("launch/*.py")),
        (os.path.join("share", package_name, "config"), glob("config/*.yaml")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Demo Maintainer",
    maintainer_email="demo@example.com",
    description="Monitors odometry topic health and triggers safety stop on timeout",
    license="MIT",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "odometry_health_monitor_node = odometry_health_monitor.odometry_health_monitor_node:main",
        ],
    },
)
