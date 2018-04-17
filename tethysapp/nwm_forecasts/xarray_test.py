import xarray
import numpy as np
from datetime import datetime
#"/media/sf_NWM/nwm.20180304/analysis_assim/nwm.t*z.analysis_assim.channel_rt.tm00.conus.nc"


fn = "/media/sf_NWM/nwm.2018030[4,5]/analysis_assim/nwm.t*z.analysis_assim.channel_rt.tm00.conus.nc"
#fn = "/media/sf_NWM/nwm.20180304/forcing_analysis_assim/nwm.t*z.analysis_assim.forcing.tm00.conus.nc
#fn = "/projects/water/nwm/data/nomads/nwm.*/analysis_assim/nwm.t*z.analysis_assim.channel_rt.tm00.conus.nc"

s = datetime.now()
ds = xarray.open_mfdataset(fn,
                           concat_dim="time",
                           chunks={"feature_id": 50000}
                           )

t_old = np.array([], dtype=np.datetime64)
t = ds.coords["time"].values

t_old = np.append(t_old, t)

ts_old = np.array([], dtype=np.float64)
ts = ds["streamflow"].loc[:, 7771045].values
ts_old = np.append(ts_old, ts)

#from datetime import datetime, timedelta
#t = datetime.strptime("20180305", "%Y%m%d")

#t2 = t + timedelta(hours=3)
#print ds["streamflow"].loc[t:t2, 185].values

print len(ts)
print t
print ts
e = datetime.now()
print e - s
exit(0)