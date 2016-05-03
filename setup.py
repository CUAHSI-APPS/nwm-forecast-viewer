import os
import sys
import ast
import urllib2 as ul
from setuptools import setup, find_packages
from tethys_apps.app_installation import custom_develop_command, custom_install_command

### Apps Definition ###
app_package = 'wrf_hydro_forecasts'
release_package = 'tethysapp-' + app_package
app_class = 'wrf_hydro_forecasts.app:WrfHydroForecasts'
app_package_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tethysapp', app_package)
print app_package_dir, '********************'

### Python Dependencies ###
dependencies = ['netCDF4']

setup(
    name=release_package,
    version='0.0.1',
    description='This application allows you to visualize National Water Model forecasts for a specific NHD stream reach.',
    long_description='',
    keywords='',
    author='Michael Souffront & Curtis Rae',
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

if os.path.isdir(os.path.join(app_package_dir, 'data')):
    dirFiles = os.listdir(os.path.join(app_package_dir, 'data'))
    if len(dirFiles) == 0:
        response = ul.urlopen('https://appsdev.hydroshare.org/apps/nwm-data-explorer/api/GetFilesList/')
        responseDict = ast.literal_eval(response.read())
        if 'success' in responseDict['reason_phrase']:
            for f in responseDict['content']:
                if '.nc' in f and 'channel_rt' in f and 'georeferenced' not in f:
                    ncFile = ul.urlopen(''.join(['https://appsdev.hydroshare.org/apps/nwm-data-explorer/api/GetFile?filename=', f]))
                    with open(os.path.join(app_package_dir, 'data', f), 'wb') as output:
                        output.write(ncFile.read())
                    if len(dirFiles) > 16:
                        break

else:
    os.makedirs(os.path.join(app_package_dir, 'data'))
    response = ul.urlopen('https://appsdev.hydroshare.org/apps/nwm-data-explorer/api/GetFilesList/')
    responseDict = ast.literal_eval(response.read())
    if 'success' in responseDict['reason_phrase']:
        for f in responseDict['content']:
            if '.nc' in f and 'channel_rt' in f and 'georeferenced' not in f:
                ncFile = ul.urlopen(''.join(['https://appsdev.hydroshare.org/apps/nwm-data-explorer/api/GetFile?filename=', f]))
                with open(os.path.join(app_package_dir, 'data', f), 'wb') as output:
                    output.write(ncFile.read())
                if len(dirFiles) > 16:
                        break
