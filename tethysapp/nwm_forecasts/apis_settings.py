from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class GetDataWatermlRateThrottle_User(UserRateThrottle):
    scope = 'GetDataWatermlRateThrottle_User'
    # rate = "3600/hour"


class GetDataWatermlRateThrottle_Anon(AnonRateThrottle):
    scope = 'GetDataWatermlRateThrottle_Anon'
    # rate = "30/second"


# class SpatialQueryApiRateThrottle_User(UserRateThrottle):
#     scope = 'SpatialQueryApiRateThrottle_User'
#     #rate = "3600/hour"
#
#
# class SpatialQueryApiRateThrottle_Anon(AnonRateThrottle):
#     scope = 'SpatialQueryApiRateThrottle_Anon'
#     #rate = "30/second"


class SubsetWatershedApiRateThrottle_User(UserRateThrottle):
    scope = 'SubsetWatershedApiRateThrottle_User'
    #rate = "1800/hour"


class SubsetWatershedApiRateThrottle_Anon(AnonRateThrottle):
    scope = 'SubsetWatershedApiRateThrottle_Anon'
    #rate = "20/hour"
