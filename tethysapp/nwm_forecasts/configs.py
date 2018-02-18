from django.conf import settings
from .app import nwmForecasts as app

app_workspace = app.get_app_workspace()
# comid = 18228725

local_vm_test = True
local_vm_test_data_date = "20170419"

app_dir = '/projects/water/nwm/data/'
if local_vm_test:
    transition_date_v11 = '20170418'  # local vm
else:
    transition_date_v11 = "20170508"
transition_timestamp_v11_AA = "12"
transition_timestamp_v11_SR = "11"
transition_timestamp_v11_MR = "12"
transition_timestamp_v11_LR = "00"

nwm_viewer_subsetting_soft_time_limit = int(getattr(settings, "NWM_VIEWER_SUBSETTING_SOFT_TIME_LIMIT", 1200)) # in seconds
nwm_viewer_subsetting_time_limit = int(getattr(settings, "NWM_VIEWER_SUBSETTING_TIME_LIMIT", 1800))  # in seconds
nwm_viewer_subsetting_rate_limit = getattr(settings, "NWM_VIEWER_SUBSETTING_RATE_LIMIT", "10/m")  # request pre min
nwm_viewer_subsetting_clean_up_minute = getattr(settings, "NWM_VIEWER_SUBSETTING_CLEAN_UP_MINUTE", "*/1")
nwm_viewer_subsetting_clean_up_hour = getattr(settings, "NWM_VIEWER_SUBSETTING_CLEAN_UP_HOUR", "*/1")
nwm_viewer_subsetting_result_life_minute = int(getattr(settings, "NWM_VIEWER_SUBSETTING_RESULT_LIFE_MINUTE", 60))  # in minutes

date_string_AA_oldest = "2016-06-09"

# path to sqlite spatial db file
db_file_path = "/projects/hydroshare/apps/apps_common_files/nwm.sqlite"
# full path to original NWM output folder (for subsetting)
netcdf_folder_path = "/projects/water/nwm/data/nomads/"

# how many days of data is stored in nomads folder
nomads_data_days = 40
