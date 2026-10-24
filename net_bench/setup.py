from setuptools import setup

package_name = "net_bench"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", ["resource/" + package_name]),
        ("share/" + package_name, ["package.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="Aayan Hossain",
    maintainer_email="aayan.hossain@torontomu.ca",
    description="Rover-to-base-station ROS 2 link benchmark",
    license="MIT",
    entry_points={
        "console_scripts": [
            "echo = net_bench.echo_node:main",
            "logger = net_bench.logger_node:main",
        ],
    },
)
