from django.core.exceptions import ImproperlyConfigured
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class UserRateThrottle_modified(UserRateThrottle):

    def __init__(self):
        try:
            # first try reading rate setting from settings.py
            self.rate = self.get_rate()
        except ImproperlyConfigured:
            # if not set, read rate setting from class
            pass

        self.num_requests, self.duration = self.parse_rate(self.rate)

    def get_cache_key(self, request, view):
        if request.user.is_authenticated:
            ident = request.user.pk
        else:
            # only throttle authenticated user
            return None

        return self.cache_format % {
            'scope': self.scope,
            'ident': ident
        }


class AnonRateThrottle_modified(AnonRateThrottle):
    def __init__(self):
        try:
            self.rate = self.get_rate()
        except ImproperlyConfigured:
            pass

        self.num_requests, self.duration = self.parse_rate(self.rate)


# WML User Burst
class GetDataWatermlRateThrottle_User(UserRateThrottle_modified):
    scope = 'GetDataWatermlRateThrottle_User'
    rate = "60/min"

# WML User Sustained
class GetDataWatermlRateThrottle_User_Sustained(UserRateThrottle_modified):
    scope = 'GetDataWatermlRateThrottle_User_Sustained'
    rate = "1800/day"

# WML Anon Burst
class GetDataWatermlRateThrottle_Anon(AnonRateThrottle_modified):
    scope = 'GetDataWatermlRateThrottle_Anon'
    rate = "6/min"

# WML Anon Sustained
class GetDataWatermlRateThrottle_Anon_Sustained(AnonRateThrottle_modified):
    scope = 'GetDataWatermlRateThrottle_Anon_Sustained'
    rate = "180/day"

# Subset User Burst
class SubsetWatershedApiRateThrottle_User(UserRateThrottle_modified):
    scope = 'SubsetWatershedApiRateThrottle_User'
    rate = "60/min"

# Subset User Sustained
class SubsetWatershedApiRateThrottle_User_Sustained(UserRateThrottle_modified):
    scope = 'SubsetWatershedApiRateThrottle_User_Sustained'
    rate = "1800/day"

# Subset Anon Burst
class SubsetWatershedApiRateThrottle_Anon(AnonRateThrottle_modified):
    scope = 'SubsetWatershedApiRateThrottle_Anon'
    rate = "6/min"

# Subset Anon Sustained
class SubsetWatershedApiRateThrottle_Anon_Sustained(AnonRateThrottle_modified):
    scope = 'SubsetWatershedApiRateThrottle_Anon_Sustained'
    rate = "180/day"
