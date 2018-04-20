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
    rate = "2000/day"

# WML Anon Burst
class GetDataWatermlRateThrottle_Anon(AnonRateThrottle_modified):
    scope = 'GetDataWatermlRateThrottle_Anon'
    rate = "3/min"

# WML Anon Sustained
class GetDataWatermlRateThrottle_Anon_Sustained(AnonRateThrottle_modified):
    scope = 'GetDataWatermlRateThrottle_Anon_Sustained'
    rate = "200/day"

# Subset User Burst
class SubsetWatershedApiRateThrottle_User(UserRateThrottle_modified):
    scope = 'SubsetWatershedApiRateThrottle_User'
    rate = "60/min"

# Subset User Sustained
class SubsetWatershedApiRateThrottle_User_Sustained(UserRateThrottle_modified):
    scope = 'SubsetWatershedApiRateThrottle_User_Sustained'
    rate = "2000/day"

# Subset Anon Burst
class SubsetWatershedApiRateThrottle_Anon(AnonRateThrottle_modified):
    scope = 'SubsetWatershedApiRateThrottle_Anon'
    rate = "3/min"

# Subset Anon Sustained
class SubsetWatershedApiRateThrottle_Anon_Sustained(AnonRateThrottle_modified):
    scope = 'SubsetWatershedApiRateThrottle_Anon_Sustained'
    rate = "200/day"
