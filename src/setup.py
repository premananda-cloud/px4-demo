from setuptools import find_packages, setup

package_name = 'agere_rl'

setup(
    name=package_name,
    version='0.0.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='you',
    maintainer_email='you@example.com',
    description='RL agent nodes for the PX4 offboard-control demo pipeline',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'rl_agent = agere_rl.rl_agent:main',
            'test_node = agere_rl.test_node:main',
        ],
    },
)
