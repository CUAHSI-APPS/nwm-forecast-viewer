#  netcdf and nco are installed and discoverable in PATH
#  GDAL_DATA is defined
#  all above paths are set as Pycharm environment variables (for PATH new item needs to append to existing PATH)
#  mount NWM data to /projects/water/nwm/data
        # View Time Series data (create_symbolic.py)
        # Subsetting data: /projects/water/nwm/data/nomads
# subset_nwm_netcdf is installed
# nwm.sqlite: "/projects/hydroshare/apps/apps_common_files/nwm.sqlite"
# for local debug, change config.py
# rabbitmq-server installed in system and "rabbitmq-plugins enable rabbitmq_management"
# memcached installed in system
# tornado 5.1.1, celery, flower, python-memcached, python-memcached-stats install in Tethys Python env
# memcached and celery configed in django settings.py

#0 start tethys db: tstartdb
#1 start tethys
#2 start rabbitmq-server and memcached services
#3 start celery: celery -A tethys_portal.tethys_celery:app worker --loglevel=DEBUG -E
#4 start flower: celery flower -A tethys_portal
#5 check rabbitmq portal at port 15672 (guest/guest) and flower portal at port 5555
#7 config api throttling in settings.py, otherwise anonymous api call would be prohibited

REST_FRAMEWORK = {
    'NUM_PROXIES': 1,
    'DEFAULT_THROTTLE_CLASSES': (
        'rest_framework.throttling.AnonRateThrottle', # otherwise anonymous api call would be prohibited
        #'rest_framework.throttling.UserRateThrottle'
    ),
    'DEFAULT_THROTTLE_RATES': {
        ## default
        'anon': '120/min',
        #'user': '120/min',

        ## specific api
        'GetDataWatermlRateThrottle_User': "60/min",
        'GetDataWatermlRateThrottle_User_Sustained': "1800/day",
        'GetDataWatermlRateThrottle_Anon': '6/min',
        'GetDataWatermlRateThrottle_Anon_Sustained': '180/day',

        'SubsetWatershedApiRateThrottle_User': '60/min',
        'SubsetWatershedApiRateThrottle_User_Sustained': '1800/day',
        'SubsetWatershedApiRateThrottle_Anon': '6/min',
        'SubsetWatershedApiRateThrottle_Anon_Sustained': '180/day',
    },
    # 'DEFAULT_PERMISSION_CLASSES': (
    #     'rest_framework.permissions.IsAuthenticated',
    # ),
    # 'DEFAULT_AUTHENTICATION_CLASSES': (
    #     'rest_framework.authentication.TokenAuthentication',
    # )
}
