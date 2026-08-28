import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'usv_gcs'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='parkseeun',
    maintainer_email='parkse1010@gmail.com',
    description='USV ground control station nodes (GUI, joystick teleop)',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'joy_to_cmd_node = usv_gcs.joy_to_cmd_node:main',
            'gui_main_node = usv_gcs.gui_main_node:main',
        ],
    },
)
