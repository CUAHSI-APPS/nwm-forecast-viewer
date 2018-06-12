import os
import datetime
import re
import netCDF4 as nc
import numpy as np
import json
import logging

from configs import *
from django.http import JsonResponse

logger = logging.getLogger(__name__)

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


def getTimeSeries(archive, config, geom, var, comid, date, endDate, time, member=''):

    app_dir=nwm_data_path_dict["view"][archive]

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


def _get_netcdf_data(request):

    if request.method == 'GET':
        get_data = request.GET
        ts_pairs_data = {}

        try:
            archive = get_data.get("archive", "rolling")
            app_dir = nwm_data_path_dict["view"][archive]
            config = get_data['config']
            geom = get_data['geom']
            var = get_data['variable']

            if geom != 'land' and geom != 'forcing':
                comid = int(get_data['COMID'])
            else:
                comid = get_data['COMID']

            startDate = get_data['startDate']
            dateDir = startDate.replace('-', '')

            if config == 'short_range' or config == 'medium_range':

                time = get_data['time']
                timeCheck = ''.join(['t', time, 'z'])
                if geom == "forcing":
                    if local_vm_test:
                        localFileDir = os.path.join(app_dir, "fe_" + config, dateDir)  # local test
                    else:
                        localFileDir = os.path.join(app_dir, "forcing_" + config, dateDir)
                else:
                    localFileDir = os.path.join(app_dir, config, dateDir)

                if int(dateDir) < int(transition_date_v11) or (int(dateDir) == int(transition_date_v11) and timestamp_early_than_transition_v11(timeCheck, transition_timestamp_v11_SR)):
                    # v1.0
                    if config == 'medium_range':
                        timeCheck = "t06z"  # v1.0 medium range only has t06z
                    nc_files = sorted([x for x in os.listdir(localFileDir) if geom in x and timeCheck in x
                                      and "georeferenced" in x and x.endswith('.nc')])
                    ts_pairs_data[str(comid)] = processNCFiles(localFileDir, nc_files, geom, comid, var, version="v1.0")
                elif int(dateDir) < int(transition_date_v12) or (int(dateDir) == int(transition_date_v12) and timestamp_early_than_transition_v11(timeCheck, transition_timestamp_v12_SR)):
                    # v1.1
                    nc_files = sorted([x for x in os.listdir(localFileDir) if geom in x and timeCheck in x
                                       and "georeferenced" not in x and x.endswith('.nc')])
                    ts_pairs_data[str(comid)] = processNCFiles(localFileDir, nc_files, geom, comid, var)
                else:
                    # v1.2
                    nc_files = sorted([x for x in os.listdir(localFileDir) if geom in x and timeCheck in x
                                       and "georeferenced" not in x and x.endswith('.nc')])
                    ts_pairs_data[str(comid)] = processNCFiles(localFileDir, nc_files, geom, comid, var)

                return JsonResponse({
                    "success": "Data analysis complete!",
                    "ts_pairs_data": json.dumps(ts_pairs_data)
                })

            elif config == 'analysis_assim':

                endDate = get_data['endDate'].replace('-', '')

                if geom == "forcing":
                    localFileDir_v10 = os.path.join(app_dir, "fe_analysis_assim")
                    if local_vm_test:
                        localFileDir_v11 = os.path.join(app_dir, "fe_analysis_assim")  # local vm
                    else:
                        localFileDir_v11 = os.path.join(app_dir, "forcing_analysis_assim")
                else:
                    localFileDir_v10 = os.path.join(app_dir, config)
                    localFileDir_v11 = localFileDir_v10

                nc_files_v10 = sorted([x for x in os.listdir(localFileDir_v10) if (geom in x if geom != "forcing" else "fe" in x)
                                       and 'tm00' in x
                                       and "georeferenced" in x
                                       and x.endswith('.nc')
                                       and int(x.split('.')[1]) >= int(dateDir)
                                       and (int(x.split('.')[1]) <= int(endDate) if int(endDate) < int(transition_date_v11) else int(x.split('.')[1]) <= int(transition_date_v11) and (timestamp_early_than_transition_v11(x, transition_timestamp_v11_AA) if transition_date_v11 in x else True))
                                       ])

                print nc_files_v10

                nc_files_v11 = sorted([x for x in os.listdir(localFileDir_v11) if geom in x
                                       and (int(x.split('.')[1]) >= int(dateDir) if int(dateDir) > int(transition_date_v11) else int(x.split('.')[1]) >= int(transition_date_v11) and ((not timestamp_early_than_transition_v11(x, transition_timestamp_v11_AA)) if transition_date_v11 in x else True))
                                       #and int(x.split('.')[1]) <= int(endDate)
                                       and (int(x.split('.')[1]) <= int(endDate) if int(endDate) < int(transition_date_v12) else int(x.split('.')[1]) <= int(transition_date_v12) and (timestamp_early_than_transition_v11(x,transition_timestamp_v12_AA) if transition_date_v12 in x else True))
                                       and 'tm00' in x
                                       and "georeferenced" not in x
                                       and x.endswith('.nc')])
                print nc_files_v11

                nc_files_v12 = sorted([x for x in os.listdir(localFileDir_v11) if geom in x
                                       and (int(x.split('.')[1]) >= int(dateDir) if int(dateDir) > int(transition_date_v12) else int(x.split('.')[1]) >= int(transition_date_v12) and ((
                                                                                                        not timestamp_early_than_transition_v11(
                                                                                                            x,
                                                                                                            transition_timestamp_v12_AA)) if transition_date_v12 in x else True))
                                       and int(x.split('.')[1]) <= int(endDate)
                                       and 'tm00' in x
                                       and "georeferenced" not in x
                                       and x.endswith('.nc')])

                print nc_files_v12

                start_time = None
                q_list = []
                if len(nc_files_v10) > 0:
                    v10_data = processNCFiles(localFileDir_v10, nc_files_v10, geom, comid, var, config="analysis_assim", version="v1.0")
                    start_time = v10_data[0]
                    q_list = v10_data[1]

                if len(nc_files_v11) > 0:
                    v11_data = processNCFiles(localFileDir_v11, nc_files_v11, geom, comid, var)
                    if start_time is None:
                        start_time = v11_data[0]
                    q_list = q_list + v11_data[1]

                if len(nc_files_v12) > 0:
                    v12_data = processNCFiles(localFileDir_v11, nc_files_v12, geom, comid, var)
                    if start_time is None:
                        start_time = v12_data[0]
                    q_list = q_list + v12_data[1]

                ts_pairs_data[str(comid)] = [start_time, q_list, "notLong"]

                return JsonResponse({
                    "success": "Data analysis complete!",
                    "ts_pairs_data": json.dumps(ts_pairs_data)
                })

            elif config == 'long_range':
                if 'lag' in get_data:
                    lag = get_data['lag']
                    if len(lag) == 0:
                        raise Exception("Parameter 'lag' is required for long range")
                    lag = lag.split(",")
                else:
                    raise Exception("Parameter 'lag' is required for long range")

                q_out_group = []
                for timeCheck in lag:
                    if "t" != timeCheck[0]:
                        timeCheck = "t" + timeCheck

                    localFileDir = os.path.join(app_dir, config, dateDir)

                    q_out_1 = []
                    q_out_2 = []
                    q_out_3 = []
                    q_out_4 = []

                    if geom == 'channel_rt':
                        if int(dateDir) < int(transition_date_v11) or (int(dateDir) == int(transition_date_v11) and timestamp_early_than_transition_v11(timeCheck, transition_timestamp_v11_LR)):
                            # v1.0
                            nc_files_1 = sorted([x for x in os.listdir(localFileDir) if
                                                 'channel_rt_1' in x and timeCheck in x
                                                 and "georeferenced" in x and x.endswith('.nc')])
                            nc_files_2 = sorted([x for x in os.listdir(localFileDir) if
                                                 'channel_rt_2' in x and timeCheck in x
                                                 and "georeferenced" in x and x.endswith('.nc')])
                            nc_files_3 = sorted([x for x in os.listdir(localFileDir) if
                                                 'channel_rt_3' in x and timeCheck in x
                                                 and "georeferenced" in x and x.endswith('.nc')])
                            nc_files_4 = sorted([x for x in os.listdir(localFileDir) if
                                                 'channel_rt_4' in x and timeCheck in x
                                                 and "georeferenced" in x and x.endswith('.nc')])

                            local_file_path = os.path.join(localFileDir, nc_files_1[0])
                            prediction_data = nc.Dataset(local_file_path, mode="r")

                            comidList = prediction_data.variables['station_id'][:]
                            comidIndex = int(np.where(comidList == comid)[0])

                        else:
                            # v1.1
                            nc_files_1 = sorted([x for x in os.listdir(localFileDir) if
                                                 'channel_rt_1' in x and timeCheck in x
                                                 and "georeferenced" not in x and x.endswith('.nc')])
                            nc_files_2 = sorted([x for x in os.listdir(localFileDir) if
                                                 'channel_rt_2' in x and timeCheck in x
                                                 and "georeferenced" not in x and x.endswith('.nc')])
                            nc_files_3 = sorted([x for x in os.listdir(localFileDir) if
                                                 'channel_rt_3' in x and timeCheck in x
                                                 and "georeferenced" not in x and x.endswith('.nc')])
                            nc_files_4 = sorted([x for x in os.listdir(localFileDir) if
                                                 'channel_rt_4' in x and timeCheck in x
                                                 and "georeferenced" not in x and x.endswith('.nc')])

                            local_file_path = os.path.join(localFileDir, nc_files_1[0])
                            prediction_data = nc.Dataset(local_file_path, mode="r")

                            comidList = prediction_data.variables['feature_id'][:]
                            comidIndex = int(np.where(comidList == comid)[0])

                        loopThroughFiles(localFileDir, q_out_1, nc_files_1, var, comidIndex)
                        loopThroughFiles(localFileDir, q_out_2, nc_files_2, var, comidIndex)
                        loopThroughFiles(localFileDir, q_out_3, nc_files_3, var, comidIndex)
                        loopThroughFiles(localFileDir, q_out_4, nc_files_4, var, comidIndex)

                    elif geom == 'reservoir':

                        if int(dateDir) < int(transition_date_v11) or (int(dateDir) == int(transition_date_v11) and timestamp_early_than_transition_v11(timeCheck, transition_timestamp_v11_LR)):
                            # v1.0
                            nc_files_1 = sorted([x for x in os.listdir(localFileDir) if
                                                 'reservoir_1' in x and timeCheck in x
                                                 and "georeferenced" in x and x.endswith('.nc')])
                            nc_files_2 = sorted([x for x in os.listdir(localFileDir) if
                                                 'reservoir_2' in x and timeCheck in x
                                                 and "georeferenced" in x and x.endswith('.nc')])
                            nc_files_3 = sorted([x for x in os.listdir(localFileDir) if
                                                 'reservoir_3' in x and timeCheck in x
                                                 and "georeferenced" in x and x.endswith('.nc')])
                            nc_files_4 = sorted([x for x in os.listdir(localFileDir) if
                                                 'reservoir_4' in x and timeCheck in x
                                                 and "georeferenced" in x and x.endswith('.nc')])

                            local_file_path = os.path.join(localFileDir, nc_files_1[0])
                            prediction_data = nc.Dataset(local_file_path, mode="r")

                            comidList = prediction_data.variables['lake_id'][:]
                            comidIndex = int(np.where(comidList == comid)[0])

                        else:
                            # v1.1
                            nc_files_1 = sorted([x for x in os.listdir(localFileDir) if
                                                 'reservoir_1' in x and timeCheck in x
                                                 and "georeferenced" not in x and x.endswith('.nc')])
                            nc_files_2 = sorted([x for x in os.listdir(localFileDir) if
                                                 'reservoir_2' in x and timeCheck in x
                                                 and "georeferenced" not in x and x.endswith('.nc')])
                            nc_files_3 = sorted([x for x in os.listdir(localFileDir) if
                                                 'reservoir_3' in x and timeCheck in x
                                                 and "georeferenced" not in x and x.endswith('.nc')])
                            nc_files_4 = sorted([x for x in os.listdir(localFileDir) if
                                                 'reservoir_4' in x and timeCheck in x
                                                 and "georeferenced" not in x and x.endswith('.nc')])

                            local_file_path = os.path.join(localFileDir, nc_files_1[0])
                            prediction_data = nc.Dataset(local_file_path, mode="r")

                            comidList = prediction_data.variables['feature_id'][:]
                            comidIndex = int(np.where(comidList == comid)[0])

                        loopThroughFiles(localFileDir, q_out_1, nc_files_1, var, comidIndex)
                        loopThroughFiles(localFileDir, q_out_2, nc_files_2, var, comidIndex)
                        loopThroughFiles(localFileDir, q_out_3, nc_files_3, var, comidIndex)
                        loopThroughFiles(localFileDir, q_out_4, nc_files_4, var, comidIndex)

                    elif geom == 'land':
                        if int(dateDir) < int(transition_date_v11) or (int(dateDir) == int(transition_date_v11) and timestamp_early_than_transition_v11(timeCheck, transition_timestamp_v11_LR)):
                            # v1.0
                            nc_files_1 = sorted([x for x in os.listdir(localFileDir) if
                                                 'land_1' in x and timeCheck in x
                                                 and "georeferenced" in x and x.endswith('.nc')])
                            nc_files_2 = sorted([x for x in os.listdir(localFileDir) if
                                                 'land_2' in x and timeCheck in x
                                                 and "georeferenced" in x and x.endswith('.nc')])
                            nc_files_3 = sorted([x for x in os.listdir(localFileDir) if
                                                 'land_3' in x and timeCheck in x
                                                 and "georeferenced" in x and x.endswith('.nc')])
                            nc_files_4 = sorted([x for x in os.listdir(localFileDir) if
                                                 'land_4' in x and timeCheck in x
                                                 and "georeferenced" in x and x.endswith('.nc')])
                        else:
                            # v1.1
                            nc_files_1 = sorted([x for x in os.listdir(localFileDir) if
                                                 'land_1' in x and timeCheck in x
                                                 and "georeferenced" not in x and x.endswith('.nc')])
                            nc_files_2 = sorted([x for x in os.listdir(localFileDir) if
                                                 'land_2' in x and timeCheck in x
                                                 and "georeferenced" not in x and x.endswith('.nc')])
                            nc_files_3 = sorted([x for x in os.listdir(localFileDir) if
                                                 'land_3' in x and timeCheck in x
                                                 and "georeferenced" not in x and x.endswith('.nc')])
                            nc_files_4 = sorted([x for x in os.listdir(localFileDir) if
                                                 'land_4' in x and timeCheck in x
                                                 and "georeferenced" not in x and x.endswith('.nc')])

                        local_file_path = os.path.join(localFileDir, nc_files_1[0])
                        prediction_data = nc.Dataset(local_file_path, mode="r")

                        comidList = comid.split(',')
                        comidIndexY = int(comidList[0])
                        comidIndexX = int(comidList[1])

                        loopThroughFiles(localFileDir, q_out_1, nc_files_1, var, None, comidIndexY, comidIndexX)
                        loopThroughFiles(localFileDir, q_out_2, nc_files_2, var, None, comidIndexY, comidIndexX)
                        loopThroughFiles(localFileDir, q_out_3, nc_files_3, var, None, comidIndexY, comidIndexX)
                        loopThroughFiles(localFileDir, q_out_4, nc_files_4, var, None, comidIndexY, comidIndexX)

                    else:
                        return JsonResponse({'error': "Invalid netCDF file"})

                    variables = prediction_data.variables.keys()
                    if 'time' in variables:
                        time = [int(nc.num2date(prediction_data.variables['time'][0], prediction_data.variables['time'].units).strftime('%s'))]
                    else:
                        return JsonResponse({'error': "Invalid netCDF file"})
                    q_out_group.append([time, q_out_1, q_out_2, q_out_3, q_out_4, timeCheck])

                ts_pairs_data[str(comid)] = q_out_group

                return JsonResponse({
                    "success": "Data analysis complete!",
                    "ts_pairs_data": json.dumps(ts_pairs_data)
                })

        except Exception as e:
            logger.error(str(e))
            return JsonResponse({'error': 'No data found for the selected reach.'})
    else:
        return JsonResponse({'error': "Bad request. Must be a GET request."})