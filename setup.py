import os
from setuptools import setup, find_packages
from tethys_apps.app_installation import custom_develop_command, custom_install_command

### Apps Definition ###
app_package = 'nwm_forecasts'
release_package = 'tethysapp-' + app_package
app_class = 'nwm_forecasts.app:nwmForecasts'
app_package_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tethysapp', app_package)

### Python Dependencies ###
dependencies = ['netCDF4>=1.2.7', 'geojson', 'shapely', 'fiona', 'subset_nwm_netcdf>=1.1.9', "GDAL>=2.1.2"]

setup(
    name=release_package,
    version='0.0.1',
    description='This application allows you to visualize National Water Model forecasts for a specific NHD stream reach.',
    long_description='',
    keywords='',
    author='Michael Souffront & Curtis Rae & Zhiyu (Drew) Li',
    author_email='',
    url='',
    license='',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    namespace_packages=['tethysapp', 'tethysapp.' + app_package],
    include_package_data=True,
    zip_safe=False,
    install_requires=dependencies,
    cmdclass={
        'install': custom_install_command(app_package, app_package_dir, dependencies),
        'develop': custom_develop_command(app_package, app_package_dir, dependencies)
    }
)

