import os
import datetime
import re
import netCDF4 as nc
import numpy as np

from configs import *
from django.http import JsonResponse


def timestamp_early_than_transition_v11(fn, transition_timestamp):

    m = re.search("t[0-9][0-9]z", fn)
    if m is not None:
        tz = m.group(0)
        timestamp = tz[1:-1]
        return int(timestamp) < int(transition_timestamp)
    raise Exception("invalid nc file name @ {0}".format(fn))


def loopThroughFiles(localFileDir, q_out, nc_files, var, comidIndex=None, comidIndexY=None, comidIndexX=None):
    for ncf in nc_files:
        local_file_path = os.path.join(localFileDir, ncf)
        prediction_dataTemp = nc.Dataset(local_file_path, mode="r")

        if var in ['streamflow', 'inflow', 'outflow']:
            q_outT = prediction_dataTemp.variables[var][comidIndex].tolist()
            q_out.append(round(q_outT * 35.3147, 4))
        elif var == 'velocity':
            q_outT = prediction_dataTemp.variables[var][comidIndex].tolist()
            q_out.append(round(q_outT * 3.28084, 4))
        elif var == 'SNOWH':
            q_outT = prediction_dataTemp.variables[var][0, comidIndexY, comidIndexX].tolist()
            q_out.append(round(q_outT * 3.28084, 4))
        elif var == 'SNEQV':
            q_outT = prediction_dataTemp.variables[var][0, comidIndexY, comidIndexX].tolist()
            q_out.append(round((q_outT / 1000) * 3.28084, 4))
        elif var in ['FSNO']:
            q_outT = prediction_dataTemp.variables[var][0, comidIndexY, comidIndexX].tolist()
            q_out.append(round(q_outT * 100, 4))
        elif var in ['SNOWT_AVG', 'SOILSAT_TOP', 'SOILSAT']:
            q_outT = prediction_dataTemp.variables[var][0, comidIndexY, comidIndexX].tolist()
            q_out.append(round(q_outT, 4))
        elif var in ['SOIL_M', 'SOIL_T']:
            q_outT = prediction_dataTemp.variables[var][0, comidIndexY, 3, comidIndexX].tolist()
            q_out.append(round(q_outT, 4))
        elif var in ['ACCET', 'UGDRNOFF', 'SFCRNOFF', 'ACCECAN', 'CANWAT']:
            q_outT = prediction_dataTemp.variables[var][0, comidIndexY, comidIndexX].tolist()
            q_out.append(round(q_outT * 0.0393701, 4))
        elif var in ['RAINRATE', 'LWDOWN', 'PSFC', 'Q2D', 'SWDOWN', 'T2D', 'U2D', 'V2D']:
            if prediction_dataTemp.variables[var].dimensions[0] != "time":
                # v1.0 forcing data
                q_outT = prediction_dataTemp.variables[var][comidIndexY, comidIndexX].tolist()
            else:
                q_outT = prediction_dataTemp.variables[var][0, comidIndexY, comidIndexX].tolist()
            if var == "RAINRATE":
                q_out.append(round(q_outT * 141.73, 4))  # mm/sec -> in/hr
            else:
                q_out.append(round(q_outT, 4))
    return q_out


def processNCFiles(localFileDir, nc_files, geom, comid, var, version="v1.1", config=None):
    local_file_path = os.path.join(localFileDir, nc_files[0])
    prediction_data = nc.Dataset(local_file_path, mode="r")

    q_out = []
    if geom == 'channel_rt':
        if version == "v1.0":
            comidList = prediction_data.variables['station_id'][:]
        else:
            comidList = prediction_data.variables['feature_id'][:]
        comidIndex = int(np.where(comidList == comid)[0])
        loopThroughFiles(localFileDir, q_out, nc_files, var, comidIndex)
    elif geom == 'reservoir':
        if version == "v1.0":
            comidList = prediction_data.variables['lake_id'][:]
        else:
            comidList = prediction_data.variables['feature_id'][:]
        comidIndex = int(np.where(comidList == comid)[0])
        loopThroughFiles(localFileDir, q_out, nc_files, var, comidIndex)
    elif geom == 'land' or 'forcing':
        comidList = comid.split(',')
        comidIndexY = int(comidList[0])
        comidIndexX = int(comidList[1])
        loopThroughFiles(localFileDir, q_out, nc_files, var, None, comidIndexY, comidIndexX)
    else:
        return JsonResponse({'error': "Invalid netCDF file"})

    variables = prediction_data.variables.keys()
    if 'time' in variables:
        time = [int(nc.num2date(prediction_data.variables["time"][0], prediction_data.variables['time'].units).strftime('%s'))]
        print "start epoch time: {0}".format(time[0])
    elif config == "analysis_assim" and geom == "forcing" and version == 'v1.0':
        # extract values from v1.0 AA forcing file name
        # nwm.20170508.t11z.fe_analysis_assim.tm00.conus.nc_georeferenced.nc
        pattern = re.compile(r"nwm.\d\d\d\d\d\d\d\d.t\d\dz.fe_analysis_assim.tm00.conus.nc_georeferenced.nc")
        if pattern.match(nc_files[0]):
            t_obj = datetime.datetime.strptime(nc_files[0], "nwm.%Y%m%d.t%Hz.fe_analysis_assim.tm00.conus.nc_georeferenced.nc")
            time = [int(t_obj.strftime('%s'))]
            print "Parsing start epoch time from v1.0 file name {0}".format(nc_files[0])
            print "start epoch time: {0}".format(time[0])
        else:
            raise Exception({"Invalid netCDF file name: " + nc_files[0]})
    else:
        raise Exception({"Invalid netCDF file: no var 'time' " + nc_files[0]})
    return [time, q_out, 'notLong']


def format_time_series(config, startDate, ts, time, nodata_value):
    nDays = len(ts)
    if config == 'short_range':
        datelist = [datetime.datetime.strptime(startDate, "%Y-%m-%d") + datetime.timedelta(hours=x + int(time) +1) for x in range(0,nDays)]
    elif config == 'medium_range':
        datelist = [datetime.datetime.strptime(startDate, "%Y-%m-%d") + datetime.timedelta(hours=x+9) for x in range(0, nDays*3, 3)]
    elif config == 'analysis_assim':
        datelist = [datetime.datetime.strptime(startDate, "%Y-%m-%d") + datetime.timedelta(hours=x) for x in range(0, nDays)]
    elif config == 'long_range':
        datelist = [datetime.datetime.strptime(startDate, "%Y-%m-%d") + datetime.timedelta(hours=x + 6) for x in range(0, nDays*6, 6)]

    formatted_ts = []
    for i in range(0, nDays):
        formatted_val = ts[i]
        if (formatted_val is None):
            formatted_val = nodata_value
        formatted_date = datelist[i].strftime('%Y-%m-%dT%H:%M:%S')
        formatted_ts.append({'date':formatted_date, 'val':formatted_val})

    return formatted_ts


def get_site_name(config, geom, var, lat, lon, lag='', member=''):
    if lat != '':
        lat_name = "Lat: %s. " % lat
    else:
        lat_name = ''
    if lon != '':
        lon_name = "Lon: %s. " % lon
    else:
        lon_name = ''
    if lag != '':
        lag_name = ' Lag: %s. ' % lag
    else:
        lag_name = ''
    if member != '':
        mem_name = ' Member: %s. ' % member
    else:
        mem_name = ''
    conf_name = config.replace('_', ' ').title()
    geom_name = geom.replace('_rt', '').title()

    return conf_name + ', ' + geom_name + ' (' + var + '). ' + lag_name + mem_name + lat_name  + lon_name


def getTimeSeries(config, geom, var, comid, date, endDate, time, member=''):

    if config != 'long_range':
        timeCheck = ''.join(['t', time, 'z'])

        ts = []

        dateDir = date.replace('-', '')

        if config in ['short_range', 'medium_range']:
            localFileDir = os.path.join(app_dir, config, dateDir)
            nc_files = sorted([x for x in os.listdir(localFileDir) if geom in x and
                               timeCheck in x])
        elif config == 'analysis_assim':
            localFileDir = os.path.join(app_dir, config)
            nc_files = sorted([x for x in os.listdir(localFileDir) if geom in x and
                               int(x.split('.')[1]) >= int(dateDir) and
                               int(x.split('.')[1]) < int(endDate.replace('-', ''))])

        ncFile = nc.Dataset(os.path.join(localFileDir, nc_files[0]), mode="r")

        if geom == 'channel_rt':
            comidList = ncFile.variables['feature_id'][:]
            comidIndex = int(np.where(comidList == comid)[0])
            loopThroughFiles(localFileDir, ts, nc_files, var, comidIndex)
        elif geom == 'reservoir':
            comidList = ncFile.variables['feature_id'][:]
            comidIndex = int(np.where(comidList == comid)[0])
            loopThroughFiles(localFileDir, ts, nc_files, var, comidIndex)
        elif geom == 'land':
            comidList = comid.split(',')
            comidIndexY = int(comidList[0])
            comidIndexX = int(comidList[1])
            loopThroughFiles(localFileDir, ts, nc_files, var, None, comidIndexY, comidIndexX)

        return ts

    elif config == 'long_range':

        ts = []

        dateDir = date.replace('-', '')
        localFileDir = os.path.join(app_dir, config, dateDir)

        nc_files = sorted([x for x in os.listdir(localFileDir) if
                           '_'.join([geom, member]) in x and time in x])

        ncFile = nc.Dataset(os.path.join(localFileDir, nc_files[0]), mode="r")

        if geom == 'channel_rt':
            comidList = ncFile.variables['feature_id'][:]
            comidIndex = int(np.where(comidList == comid)[0])
            loopThroughFiles(localFileDir, ts, nc_files, var, comidIndex)
        elif geom == 'reservoir':
            comidList = ncFile.variables['feature_id'][:]
            comidIndex = int(np.where(comidList == comid)[0])
            loopThroughFiles(localFileDir, ts, nc_files, var, comidIndex)
        elif geom == 'land':
            comidList = comid.split(',')
            comidIndexY = int(comidList[0])
            comidIndexX = int(comidList[1])
            loopThroughFiles(localFileDir, ts, nc_files, var, None, comidIndexY, comidIndexX)

        return ts