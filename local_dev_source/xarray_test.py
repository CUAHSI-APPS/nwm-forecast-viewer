import xarray
import numpy as np
from datetime import datetime
#"/media/sf_NWM/nwm.20180304/analysis_assim/nwm.t*z.analysis_assim.channel_rt.tm00.conus.nc"


#fn = "/media/sf_NWM/nwm.2018030[4,5]/analysis_assim/nwm.t*z.analysis_assim.channel_rt.tm00.conus.nc"
#fn = "/media/sf_NWM/nwm.20180304/forcing_analysis_assim/nwm.t*z.analysis_assim.forcing.tm00.conus.nc
fn = "/projects/water/nwm/data/nomads/nwm.2018031[0-1]/analysis_assim/nwm.t*z.analysis_assim.channel_rt.tm00.conus.nc"
fn_template = "/projects/water/nwm/data/nomads/nwm.2018031{date}/medium_range/nwm.t00z.medium_range.channel_rt.f*.conus.nc"

date_list = [fn_template.format(date=str(date)) for date in range(0,1)]
print(date_list)

s = datetime.now()

t = np.array([], dtype=np.datetime64)
ts = np.array([], dtype=np.float64)
for d in date_list:
        ds = xarray.open_mfdataset(d,
                           concat_dim="time",
                           chunks={"feature_id": 50000}
                           )

        t_new = ds.coords["time"].values
        t = np.append(t, t_new)
        ts_new = ds["streamflow"].loc[:, 7771045].values
        ts =  np.append(ts, ts_new)

#from datetime import datetime, timedelta
#t = datetime.strptime("20180305", "%Y%m%d")

#t2 = t + timedelta(hours=3)
#print ds["streamflow"].loc[t:t2, 185].values

print(len(ts))
print(t)
print(ts)
e = datetime.now()
print(e - s)
exit(0)
