from setuptools import setup, find_packages
setup(
    name='InModbusSimplify',
    sdk_version='1.3.1',
    version='1.0.1',
    author='inhand',
    author_email='',
    description='',
    license='PRIVATE',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    zip_safe=False,
    install_requires=[
		'modbus_tk==1.0.0'
],
    entry_points="""
        [console_scripts]
        InModbusSimplify = Application:main
        """
)
