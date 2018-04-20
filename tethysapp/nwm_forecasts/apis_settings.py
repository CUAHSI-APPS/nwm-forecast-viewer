from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class GetDataWatermlRateThrottle_User(UserRateThrottle):
    scope = 'GetDataWatermlRateThrottle_User'
    # rate = "60/min"

class GetDataWatermlRateThrottle_User_Sustained(UserRateThrottle):
    scope = 'GetDataWatermlRateThrottle_User_Sustained'
    # rate = "3600/hour"

class GetDataWatermlRateThrottle_Anon(AnonRateThrottle):
    scope = 'GetDataWatermlRateThrottle_Anon'
    # rate = "30/second"

class GetDataWatermlRateThrottle_Anon_Sustained(AnonRateThrottle):
    scope = 'GetDataWatermlRateThrottle_Anon_Sustained'
    # rate = "500/day"


class SubsetWatershedApiRateThrottle_User(UserRateThrottle):
    scope = 'SubsetWatershedApiRateThrottle_User'
    #rate = "60/min"

class SubsetWatershedApiRateThrottle_User_Sustained(UserRateThrottle):
    scope = 'SubsetWatershedApiRateThrottle_User_Sustained'
    #rate = "5000/day"

class SubsetWatershedApiRateThrottle_Anon(AnonRateThrottle):
    scope = 'SubsetWatershedApiRateThrottle_Anon'
    #rate = "3/min"

class SubsetWatershedApiRateThrottle_Anon_Sustained(AnonRateThrottle):
    scope = 'SubsetWatershedApiRateThrottle_Anon_Sustained'
    #rate = "500/day"
