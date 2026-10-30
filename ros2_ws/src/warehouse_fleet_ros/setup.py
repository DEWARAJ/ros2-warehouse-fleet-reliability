from glob import glob
from setuptools import find_packages, setup

package_name = "warehouse_fleet_ros"

setup(
    name=package_name,
    version="0.1.0",
    packages=find_packages(),
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
        ("share/" + package_name + "/launch", glob("launch/*.launch.py")),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Dewaraj Raparthi",
    maintainer_email="dewarajraparthi@gmail.com",
    description="Warehouse fleet reliability ROS 2 nodes",
    license="MIT",
    entry_points={
        "console_scripts": [
            "fleet_controller = warehouse_fleet_ros.controller_node:main",
            "robot_worker = warehouse_fleet_ros.robot_worker_node:main",
            "fault_injector = warehouse_fleet_ros.fault_injector_node:main",
        ]
    },
)
