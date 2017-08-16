import os
import shutil
import re
import json
import tempfile
import logging
import uuid
import datetime
import pytz
import zipfile

logger = logging.getLogger(__name__)

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404, FileResponse, HttpResponse
from django.shortcuts import render_to_response
from django.views.decorators.csrf import csrf_exempt
# from django.conf import settings

from tethys_sdk.gizmos import SelectInput, ToggleSwitch, Button, DatePicker

import netCDF4 as nc
import numpy as np
import xmltodict
import shapely.geometry
from shapely import wkt
import fiona
import geojson
from osgeo import ogr
from osgeo import osr
from subset_nwm_netcdf.query import query_comids_and_grid_indices
from subset_nwm_netcdf.subset import start_subset_nwm_netcdf_job
from subset_nwm_netcdf.merge import start_merge_nwm_netcdf_job

from celery import shared_task
from celery.task import periodic_task
from celery.schedules import crontab
from django_celery_results.models import TaskResult
from django.db.models import Q

from .app import nwmForecasts as app

app_workspace = app.get_app_workspace()
# comid = 18228725

local_vm_test = True

hs_hostname = 'www.hydroshare.org'
app_dir = '/projects/water/nwm/data/'
if local_vm_test:
    transition_date_v11 = "20170419"  # local vm
else:
    transition_date_v11 = "20170508"
transition_timestamp_v11_AA = "12"
transition_timestamp_v11_SR = "11"
transition_timestamp_v11_MR = "12"
transition_timestamp_v11_LR = "00"

hydroshare_ready = True
try:
    from tethys_services.backends.hs_restclient_helper import get_oauth_hs
except Exception:
    logger.error("could not load: tethys_services.backends.hs_restclient_helper import get_oauth_hs")
    hydroshare_ready = False

date_string_AA_oldest = "2016-06-09"

def _get_current_utc_date():

    if local_vm_test:
        return "2017-04-19", "2017-04-19", "2017-04-19", "2017-04-19"

    date_string_today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    date_string_oldest = (datetime.datetime.utcnow() + datetime.timedelta(days=-30)).strftime("%Y-%m-%d")
    date_string_minus_2 = (datetime.datetime.utcnow() + datetime.timedelta(days=-2)).strftime("%Y-%m-%d")
    date_string_minus_3 = (datetime.datetime.utcnow() + datetime.timedelta(days=-3)).strftime("%Y-%m-%d")

    return date_string_today, date_string_oldest, date_string_minus_2, date_string_minus_3


def _init_page(request):
    date_string_today, date_string_oldest, _, _ = _get_current_utc_date()

    start_date = DatePicker(name='startDate',
                            display_text='Begin Date',
                            end_date='0d',
                            autoclose=True,
                            format='yyyy-mm-dd',
                            start_date=date_string_AA_oldest,
                            today_button=True,
                            initial=date_string_today)

    end_date = DatePicker(name='endDate',
                          end_date='0d',
                          autoclose=True,
                          format='yyyy-mm-dd',
                          start_date=date_string_AA_oldest,
                          today_button=True,
                          initial=date_string_today,
                          classes="hidden")

    longRangeLag00 = ToggleSwitch(display_text='', name='00z', size='mini', initial=True)
    longRangeLag06 = ToggleSwitch(display_text='', name='06z', size='mini')
    longRangeLag12 = ToggleSwitch(display_text='', name='12z', size='mini')
    longRangeLag18 = ToggleSwitch(display_text='', name='18z', size='mini')

    global hydroshare_ready
    hs_username = ""
    if hydroshare_ready:
        try:
            hs = get_oauth_hs(request)
            hs_username = hs.getUserInfo()['username']
        except Exception:
            hydroshare_ready = False

    waterml_url = ""

    if request.GET:
        # Make the waterml url query string
        config = request.GET['config']
        geom = request.GET['geom']
        variable = request.GET['variable']
        if geom != 'land' and geom != 'forcing':
            comid = request.GET['COMID']
        else:
            comid = ','.join([request.GET['Y'], request.GET['X']])
        lon = ''
        if 'lon' in request.GET:
            lon = request.GET['lon']
        lat = ''
        if 'lat' in request.GET:
            lat = request.GET['lat']
        startDate = request.GET['startDate']

        endDate = ''
        if 'endDate' in request.GET:
            endDate = request.GET['endDate']

        time = ''
        if 'time' in request.GET:
            time = request.GET['time']

        lagList = []
        if '00z' in request.GET:
            lagList.append('t00z')
        if '06z' in request.GET:
            lagList.append('t06z')
        if '12z' in request.GET:
            lagList.append('t12z')
        if '18z' in request.GET:
            lagList.append('t18z')

        lag = ','.join(lagList)
        waterml_url = '?config=%s&geom=%s&variable=%s&COMID=%s&lon=%s&lat=%s&startDate=%s&endDate=%s&time=%s&lag=%s' % \
                      (config, geom, variable, comid, lon, lat, startDate, endDate, time, lag)

        # watershed_obj_session = request.session.get("watershed", None)

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'longRangeLag00': longRangeLag00,
        'longRangeLag06': longRangeLag06,
        'longRangeLag12': longRangeLag12,
        'longRangeLag18': longRangeLag18,
        'waterml_url': waterml_url,
        'hs_ready': hydroshare_ready,
        'hs_username': hs_username,
        # 'watershed_geojson_str': watershed_obj_session['geojson_str'] if watershed_obj_session is not None else "",
        # 'watershed_attributes_str': json.dumps(watershed_obj_session['attributes']) if watershed_obj_session is not None else "",
        "date_string_today": date_string_today,
        "date_string_oldest": date_string_oldest,
        "date_string_AA_oldest": date_string_AA_oldest,
    }
    return context


@login_required()
def home(request):
    """
    Controller for the app home page.
    """

    context = _init_page(request)
    return render(request, 'nwm_forecasts/home.html', context)


def subset(request):
    """
    Controller for the app home page.
    """

    context = _init_page(request)
    return render(request, 'nwm_forecasts/download.html', context)


def timestamp_early_than_transition_v11(fn, transition_timestamp):

    m = re.search("t[0-9][0-9]z", fn)
    if m is not None:
        tz = m.group(0)
        timestamp = tz[1:-1]
        return int(timestamp) < int(transition_timestamp)
    raise Exception("invalid nc file name @ {0}".format(fn))


def get_netcdf_data(request):
    if request.method == 'GET':
        get_data = request.GET
        ts_pairs_data = {}

        try:
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
                else:
                    # v1.1
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
                                       and int(x.split('.')[1]) <= int(endDate)
                                       and 'tm00' in x
                                       and "georeferenced" not in x
                                       and x.endswith('.nc')])
                print nc_files_v11
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
            print str(e)
            return JsonResponse({'error': 'No data found for the selected reach.'})
    else:
        return JsonResponse({'error': "Bad request. Must be a GET request."})


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
        elif var in ['FSNO', 'SOILSAT_TOP', 'SOILSAT', 'CANWAT', 'SNOWT_AVG']:
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


@login_required()
def get_hs_watershed_list(request):
    response_obj = {}
    hs_username = ""
    try:
        if not hydroshare_ready:
            raise Exception("not logged in via hydroshare")
        if request.is_ajax() and request.method == 'GET':
            resources_list = []
            hs = get_oauth_hs(request)
            if hs is None:
                response_obj['error'] = 'You must be signed in through HydroShare to access this feature. ' \
                                        'Please log out and then sign in again using your HydroShare account.'
            else:
                owner = None
                try:
                    owner = hs.getUserInfo()['username']
                    hs_username = owner
                except Exception:
                    pass

                # loop through all Generic and Feature res current user owns
                valid_res_types = ['GenericResource', 'GeographicFeatureResource']

                for resource in hs.getResourceList(types=valid_res_types, owner=owner):
                #for resource in hs.getResourceList(types=valid_res_types):
                    res_id = resource['resource_id']
                    try:
                        # generic res has "watershed" in keywords
                        # has filename *.geojson
                        if resource["resource_type"] == "GenericResource":
                            sci_meta = hs.getScienceMetadata(res_id)
                            for subject in sci_meta["subjects"]:
                                if subject["value"].lower() == "watershed":
                                    for res_file in hs.getResourceFileList(res_id):
                                        filename = os.path.basename(res_file['url'])
                                        if os.path.splitext(filename)[1] in ".geojson":
                                            resources_list.append({
                                                'title': resource['resource_title'],
                                                'id': res_id,
                                                'owner': resource['creator'],
                                                'filename': filename
                                            })
                        else:
                            # feature res
                            # type of "polygon" or "multipolygon"
                            # has .prj file
                            doc = xmltodict.parse(hs.getScienceMetadataRDF(res_id))
                            geom_type = \
                            doc["rdf:RDF"]["rdf:Description"][0]["hsterms:GeometryInformation"]["rdf:Description"][
                                "hsterms:geometryType"]
                            if geom_type.lower() in ["polygon", "multipolygon"]:
                                has_prj = False
                                shp_filename = None
                                for res_file in hs.getResourceFileList(res_id):
                                    filename = os.path.basename(res_file['url'])
                                    if os.path.splitext(filename)[1] in ".shp":
                                        shp_filename = filename
                                    elif os.path.splitext(filename)[1] in ".prj":
                                        has_prj = True
                                if has_prj:
                                    resources_list.append({
                                        'title': resource['resource_title'],
                                        'id': res_id,
                                        'owner': resource['creator'],
                                        'filename': shp_filename
                                    })

                    except Exception as ex:
                        logger.exception(ex)
                        logger.error("Failed res in get_hs_watershed_list: " + str(resource))

                resources_json = json.dumps(resources_list)

                response_obj['success'] = 'Resources obtained successfully.'
                response_obj['resources'] = resources_json
                response_obj['hs_username'] = hs_username
        else:
            raise Exception("not a ajax GET request")

    except Exception as ex:
        logger.exception(ex)
        response_obj = {"error": "Failed to load resources from HydroShare. Did you sign in with your HydroShare account?"}
    finally:
        return JsonResponse(response_obj)


@login_required()
def load_watershed(request):

    if not hydroshare_ready:
        raise Exception("not logged in via hydroshare")

    tmp_dir = None
    try:
        if request.is_ajax() and request.method == 'POST':

            res_id = str(request.POST['res_id'])
            filename = str(request.POST['filename'])
            res_title = request.POST.get('res_title')
            add_to_hs = request.POST.get('add_to_hs')
            uploaded_files = request.FILES.getlist('files')
            tmp_dir = tempfile.mkdtemp()

            #save local files
            shp_geojson_local_path = None
            f_path_list = []
            for f in uploaded_files:
                f_name = f.name
                f_path = os.path.join(tmp_dir, f_name)
                if f_path.lower().endswith(".shp"):
                    shp_geojson_local_path = f_path
                elif f_path.lower().endswith(".geojson"):
                    shp_geojson_local_path = f_path
                with open(f_path, 'wb') as f_local:
                    f_local.write(f.read())
                    f_path_list.append(f_path)

            if add_to_hs == "true" and len(uploaded_files) > 0 and shp_geojson_local_path:  # upload to hydroshare
                logger.debug("pushing to hs")
                logger.debug(shp_geojson_local_path)
                res_id = _add_shp_geojson_to_hs(request, shp_geojson_local_path, res_title)
                logger.debug("done pushing to hs")

            response_obj = _get_geojson_from_hs_resource(request, res_id, filename, shp_geojson_local_path)

            shutil.rmtree(tmp_dir)

            return JsonResponse(response_obj)

    except Exception as ex:
        logger.exception(ex)
        return JsonResponse({'error': "Failed to load watershed"})
    finally:
        if tmp_dir is not None and os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)


def _add_shp_geojson_to_hs(request, shp_geojson_local_path, res_title):

    logger.debug("pushing to hs")
    hs = get_oauth_hs(request)

    r_type = None
    r_file = None
    if shp_geojson_local_path.lower().endswith('.geojson'):
        r_type = "GenericResource"
        r_file = shp_geojson_local_path
    elif shp_geojson_local_path.lower().endswith('.shp'):
        r_type = "GeographicFeatureResource"
        dir_path = os.path.dirname(shp_geojson_local_path)
        logger.debug(dir_path)
        zip_file_path = os.path.join(dir_path, "hs_shp.zip")
        _zip_folder_contents(zip_file_path, dir_path, skip_list=["hs_shp.zip"])
        r_file = zip_file_path
    else:
        raise Exception("not shp or geojson")
    logger.debug(r_file)
    logger.debug(type(r_file))
    res_id = hs.createResource(r_type,
                               res_title,
                               keywords=["watershed"],
                               resource_file=str(r_file)
                               )
    logger.debug("Created on hs @" + str(res_id))
    return res_id


def _get_geojson_from_hs_resource(request, res_id, filename, shp_geojson_local_path):

    response_obj = {}
    try:
        hs = get_oauth_hs(request)

        if filename.endswith('.geojson') or (shp_geojson_local_path is not None and shp_geojson_local_path.lower().endswith(".geojson")):
            # geojson file
            if (shp_geojson_local_path is not None) and shp_geojson_local_path.lower().endswith(".geojson"):
                with open(shp_geojson_local_path) as geojson_data:
                    geojson_obj = geojson.load(geojson_data)
            else:
                geojson_str = str(hs.getResourceFile(pid=res_id, filename=filename).next())
                geojson_obj = geojson.loads(geojson_str)

            geojson_geom_first = geojson_obj
            if geojson_obj.type.lower() == "featurecollection":
                geojson_geom_first = geojson_obj.features[0].geometry
            shape_obj = shapely.geometry.asShape(geojson_geom_first)
            response_obj['type'] = 'geojson'
            in_proj_type = "epsg"
            in_proj_value = 4326

        elif filename.endswith('.shp') or (shp_geojson_local_path is not None and shp_geojson_local_path.lower().endswith(".shp")):
            # shapefile
            tmp_dir = tempfile.mkdtemp()
            if (shp_geojson_local_path is not None) and shp_geojson_local_path.lower().endswith(".shp"):
                with open(shp_geojson_local_path.replace('.shp', '.prj'), 'r') as content_file:
                    proj_str_raw = content_file.read()
                    proj_str = proj_str_raw.replace('\n', '')
                shp_path = shp_geojson_local_path
            else:
                proj_str_raw = str(hs.getResourceFile(pid=res_id, filename=filename.replace('.shp', '.prj')).next())
                proj_str = proj_str_raw.replace('\n', '')
                for ext in [".prj", ".dbf", ".shx", ".shp"]:
                    fn = filename.replace(".shp", ext)
                    shp_path = os.path.join(tmp_dir, fn)
                    with open(shp_path, "wb+") as shp:
                        for chunk in hs.getResourceFile(pid=res_id, filename=fn):
                            shp.write(chunk)

            response_obj['type'] = 'shp'
            in_proj_type = "esri"
            in_proj_value = proj_str
            shp_obj = fiona.open(shp_path)
            first_feature_obj = next(shp_obj)
            shape_obj = shapely.geometry.shape(first_feature_obj["geometry"])
            shutil.rmtree(tmp_dir)
        else:
            raise Exception("Failed to read geometry ")

        # convert 3D geom to 2D
        if shape_obj.has_z:
            wkt2D = shape_obj.wkt
            shape_obj = wkt.loads(wkt2D)
        if shape_obj.geom_type.lower() == "multipolygon":
            polygon_exterior_linearring = shape_obj[0].exterior
        elif shape_obj.geom_type.lower() == "polygon":
            polygon_exterior_linearring = shape_obj.exterior
        else:
            raise Exception("Input Geometry is not Polygon")

        polygon_exterior_linearring_shape_obj = shapely.geometry.Polygon(polygon_exterior_linearring)

        # use gdal for coordinate re-projection
        wkt_3857 = reproject_wkt_gdal(in_proj_type=in_proj_type,
                                      in_proj_value=in_proj_value,
                                      out_proj_type="epsg",
                                      out_proj_value=3857,
                                      in_geom_wkt=polygon_exterior_linearring_shape_obj.wkt)
        geojson_str = ogr.CreateGeometryFromWkt(wkt_3857).ExportToJson()
        resource_md = None
        if not shp_geojson_local_path:
            resource_md = hs.getSystemMetadata(res_id)
        watershed = {
                        "geojson_str": geojson_str,
                        "attributes":
                            {
                                "res_id": res_id if resource_md else "local_file",
                                "filename": filename if resource_md else os.path.basename(shp_geojson_local_path),
                                "title": resource_md['resource_title'] if resource_md else "local file"
                            }
                    }

        # session_key = "watershed"
        # if session_key in request.session:
        #     del request.session[session_key]
        # request.session[session_key] = watershed
        # request.session.modified = True

        response_obj['success'] = 'Geojson obtained successfully.'
        response_obj['watershed'] = watershed

    except Exception as e:
        logger.exception(e)
        response_obj['error'] = 'Failed to load watershed.'

    return response_obj


def reproject_wkt_gdal(in_proj_type,
                       in_proj_value,
                       out_proj_type,
                       out_proj_value,
                       in_geom_wkt):

    try:
        if 'GDAL_DATA' not in os.environ:
            raise Exception("Environment variable 'GDAL_DATA' not found!")

        source = osr.SpatialReference()
        if in_proj_type.lower() == "epsg":
            source.ImportFromEPSG(in_proj_value)
        elif in_proj_type.lower() == "proj4":
            source.ImportFromProj4(in_proj_value)
        elif in_proj_type.lower() == "esri":
            source.ImportFromESRI([in_proj_value])
        else:
            raise Exception("unsupported projection type: " + out_proj_type)

        target = osr.SpatialReference()
        if out_proj_type.lower() == "epsg":
            target.ImportFromEPSG(out_proj_value)
        elif out_proj_type.lower() == "proj4":
            target.ImportFromProj4(out_proj_value)
        elif out_proj_type.lower() == "esri":
            target.ImportFromESRI([out_proj_value])
        else:
            raise Exception("unsupported projection type: " + out_proj_type)

        transform = osr.CoordinateTransformation(source, target)

        geom_gdal = ogr.CreateGeometryFromWkt(in_geom_wkt)
        geom_gdal.Transform(transform)

        return geom_gdal.ExportToWkt()

    except Exception as ex:
        logger.error("in_proj_type: {0}".format(in_proj_type))
        logger.error("in_proj_value: {0}".format(in_proj_value))
        logger.error("out_proj_type: {0}".format(out_proj_type))
        logger.error("out_proj_value: {0}".format(out_proj_value))
        logger.error(str(type(ex)) + " " + ex.message)
        raise ex


@login_required()
def upload_to_hydroshare(request):
    temp_dir = None
    try:
        if not hydroshare_ready:
            raise Exception("not logged in via hydroshare")
        return_json = {}
        if request.method == 'POST':
            post_data = request.POST

            if request.is_secure():
                front_end = 'https://'
            else:
                front_end = 'http://'

            waterml_url = front_end + request.get_host() + post_data['waterml_link']

            r_title = post_data['title']
            r_abstract = post_data['abstract']
            r_keywords_raw = post_data['keyword']
            r_keywords = r_keywords_raw.split(',')
            r_type = 'RefTimeSeriesResource'

            r_public = post_data['public']
            hs = get_oauth_hs(request)

            ref_type = "rest"
            metadata = []
            metadata.append({"referenceurl": {"value": waterml_url, "type": ref_type}})

            res_id = hs.createResource(r_type,
                                       r_title,
                                       resource_file=None,
                                       keywords=r_keywords,
                                       abstract=r_abstract,
                                       metadata=json.dumps(metadata))

            if res_id is not None:
                if r_public.lower() == 'true':
                    hs.setAccessRules(res_id, public=True)
                return_json['success'] = 'File uploaded successfully!'
                return_json['newResource'] = res_id
            else:
                raise

    except ObjectDoesNotExist as e:
        # print ("ObjectDoesNotExist")
        # print str(e)
        return_json['error'] = 'Login timed out! Please re-sign in with your HydroShare account.'
    except TokenExpiredError as e:
        # print str(e)
        return_json['error'] = 'Login timed out! Please re-sign in with your HydroShare account.'
    except Exception, err:
        if "401 Unauthorized" in str(err):
            return_json['error'] = 'Username or password invalid.'
        elif "400 Bad Request" in str(err):
            return_json['error'] = 'File uploaded successfully despite 400 Bad Request Error.'
        else:
            traceback.print_exc()
            return_json['error'] = 'HydroShare rejected the upload for some reason.'
    finally:
        if temp_dir != None:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        return JsonResponse(return_json)


def _find_all_files_in_folder(directory, searching_text, match_pattern="endswith", full_path=True):

    files_list = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            found_f = None
            if match_pattern == "endswith":
                if file.endswith(searching_text):
                    found_f = file
            elif match_pattern == "startswith":
                if file.startswith(searching_text):
                    found_f = file
            elif match_pattern == "in":
                if searching_text in os.path.basename(file):
                    found_f = file
            elif match_pattern == "equals":
                if searching_text == os.path.basename(file):
                    found_f = file
            else:
                continue
            if full_path:
                files_list.append(os.path.join(root, found_f))
            else:
                files_list.append(found_f)
    return files_list


@login_required()
def subset_watershed(request):

    job_folder_path = None
    binary_file_name = None
    binary_file_path = None
    upload_to_hydroshare = False

    try:
        if not hydroshare_ready:
            raise Exception("not logged in via hydroshare")
        if request.method == 'POST':

            request_dict = json.loads(request.body)
            if "hydroshare" in request_dict:
                upload_to_hydroshare = True

            job_id, job_folder_path = _perform_subset(request_dict['watershed_geometry'],
                                                       int(request_dict['watershed_epsg']),
                                                       request_dict['subset_parameter'])

            nc_file_list = _find_all_files_in_folder(job_folder_path, ".nc")
            nc_file_list_count = len(nc_file_list)
            hs_res_type = None
            if nc_file_list_count == 1:
                # only one nc file --> netcdf resource type
                hs_res_type = "NetcdfResource"
                binary_file_path = nc_file_list[0]
                binary_file_name = os.path.basename(binary_file_path)
                pass
            elif nc_file_list_count == 0:
                # 0 --> error
                raise Exception("No netcdf file")
            else:
                # more than one nc file --> composite resource type
                hs_res_type = "CompositeResource"
                # zip it up first
                zip_file_path = job_folder_path + '.zip'
                _zip_folder_contents(zip_file_path, job_folder_path)
                binary_file_path = zip_file_path
                binary_file_name = job_id + ".zip"
                pass

            # upload to hydroshare
            if upload_to_hydroshare:
                hs = get_oauth_hs(request)
                hydroshare_dict = request_dict["hydroshare"]
                if hs_res_type == "CompositeResource":
                    resource_id = hs.createResource("CompositeResource",
                                                    hydroshare_dict["title"],
                                                    keywords=hydroshare_dict["keywords"].split(','),
                                                    abstract=hydroshare_dict["abstract"])

                    resource_id = hs.addResourceFile(resource_id, binary_file_path)

                    options = {
                                "zip_with_rel_path": os.path.basename(binary_file_path),
                                "remove_original_zip": True
                              }

                    unzipping_resp = hs.resource(resource_id).functions.unzip(options)

                elif hs_res_type == "NetcdfResource":
                    resource_id = hs.createResource("NetcdfResource",
                                                    hydroshare_dict["title"],
                                                    resource_file=binary_file_path,
                                                    keywords=hydroshare_dict["keywords"].split(','),
                                                    abstract=hydroshare_dict["abstract"])
                else:
                    raise Exception("wrong resource type")

                return JsonResponse({"status": "success", "res_id": resource_id})

            else:  # return file binary stream

                response = FileResponse(open(binary_file_path, 'rb'), content_type='application/zip' if binary_file_name
                                        .endswith(".zip") else "application/x-cdf")
                response['Content-Disposition'] = 'attachment; filename="' + '{0}"'.format(binary_file_name)
                response['Content-Length'] = os.path.getsize(binary_file_path)
                return response
        else:
            if upload_to_hydroshare:
                return JsonResponse({"status": "error"})
            else:
                return HttpResponse(status=500, content="Not a POST request")
    except Exception as ex:
        logger.exception(type(ex))
        if upload_to_hydroshare:
            return JsonResponse({"status": "error", "msg": ex.message})
        else:
            return HttpResponse(status=500, content=ex.message)
    finally:
        if job_folder_path is not None:
            if os.path.exists(job_folder_path + ".zip"):
                os.remove(job_folder_path + ".zip")
            if os.path.exists(job_folder_path):
                shutil.rmtree(job_folder_path)


@csrf_exempt
def check_subsetting_job_status(request, job_id=None):
    if not job_id:
        if request.method == 'GET':
            job_id = request.get("job_id")
        elif request.method == 'POST':
            job_id = json.loads(request.body)['job_id']
        else:
            raise Exception("Accept GET or POST.")
    if job_id:
        result = _perform_subset.AsyncResult(job_id)

        return HttpResponse(json.dumps({"status": result.state}),
                            content_type="application/json")

    return HttpResponse(json.dumps({"error": "Can not find results for job id: {0}".format(job_id)}),
                                    content_type="application/json")

@csrf_exempt
def download_subsetting_results(request, job_id=None):

    if not job_id:
        if request.method == 'GET':
            job_id = request.get("job_id")
        elif request.method == 'POST':
            job_id = json.loads(request.body)['job_id']
        else:
            raise Exception("Accept GET or POST.")

    if job_id:
        result = _perform_subset.AsyncResult(job_id)
        if result.ready():

            rslt = result.get()

            bag_save_to_path = rslt[1]
            zip_file_path = bag_save_to_path
            response = FileResponse(open(zip_file_path, 'rb'), content_type='application/zip')
            response['Content-Disposition'] = 'attachment; filename="' + '{0}.zip"'.format(job_id)
            response['Content-Length'] = os.path.getsize(bag_save_to_path)
            return response
    return Http404("Can not find results for job id: {0}".format(job_id))


@csrf_exempt
def subset_watershed_api(request):

    bag_save_to_path = None
    try:
        if request.method == 'POST':
            logger.error(request)
            request_dict = json.loads(request.body)
            watershed_geometry = request_dict['watershed_geometry']
            watershed_epsg = int(request_dict['watershed_epsg'])
            subset_parameter_dict = request_dict['subset_parameter']
            logger.error("------START: subset_watershed_api--------")

            job_id = str(uuid.uuid4())
            job_id = "subset-" + job_id

            task = _perform_subset.apply_async((watershed_geometry,
                                                       watershed_epsg,
                                                       subset_parameter_dict),
                                                        {"job_id":job_id,
                                                       "zip_results":True},
                                                       task_id=job_id,
                                                       countdown=3,
                                                        time_limit=1200,  # 20 minutes
                                                        soft_time_limit=900,  # 15 minutes
                                                        rate_limit="20/m")  # 10 request/min

            #result = create_bag_by_irods.AsyncResult(task_id)
            #if result.ready():

            # response = FileResponse(open(bag_save_to_path, 'rb'), content_type='application/zip')
            # response['Content-Disposition'] = 'attachment; filename="' + '{0}.zip"'.format(job_id)
            # response['Content-Length'] = os.path.getsize(bag_save_to_path)
            response = JsonResponse({"job_id": task.task_id, "status": task.state})
            logger.error("------END: subset_watershed_api--------")
            return response
        else:
            raise Exception("Not a POST request, Note: this api endpoint must end with a slash '/'")

    except Exception as ex:
        logger.exception(ex.message)
        logger.error("------ERROR: subset_watershed_api--------")
        return HttpResponse(status=500, content=ex.message)

    # finally:
    #     if bag_save_to_path is not None:
    #         if os.path.exists(bag_save_to_path):
    #             os.remove(bag_save_to_path)
    #         if os.path.exists(bag_save_to_path.replace(".zip", "")):
    #             shutil.rmtree(bag_save_to_path.replace(".zip", ""))


@shared_task
def _perform_subset(geom_str, in_epsg, subset_parameter_dict, job_id=None, zip_results=False):

    db_file_path = "/nwm.sqlite"

    if not job_id:
        job_id = str(uuid.uuid4())

    all_start_dt = datetime.datetime.now()
    logger.info("-------------Process Started-------------------")
    logger.info(all_start_dt)

    # geojson example
    query_type = "geojson"
    shp_path = None
    # geom_str = request_dict['watershed_geometry']
    # in_epsg = 3857  # epsg is required
    huc_id = None

    query_result_dict = query_comids_and_grid_indices(job_id=job_id,
                                                      db_file_path=db_file_path,
                                                      query_type=query_type,
                                                      shp_path=shp_path,
                                                      geom_str=geom_str,
                                                      in_epsg=in_epsg,
                                                      huc_id=huc_id)
    if query_result_dict is None:
        raise Exception("Failed to retrieve spatial query result")

    # subset_parameter_dict = request_dict['subset_parameter']

    netcdf_folder_path = "/projects/water/nwm/data/nomads/"

    # Path of output folder
    #output_folder_path = "/tmp"
    output_folder_path = app_workspace.path
    logger.error("****************************************")
    logger.error(output_folder_path)

    # shrink dimension size to cover subsetting domain only
    resize_dimension_grid = True
    resize_dimension_feature = True
    # merge resulting netcdfs
    #merge_netcdfs = subset_parameter_dict['merge']
    merge_netcdfs = True
    # remove intermediate files
    cleanup = True

    # list of simulation dates
    if len(subset_parameter_dict["endDate"]) > 0 and subset_parameter_dict["config"] == "analysis_assim":
        if int(subset_parameter_dict["endDate"].replace("-", "")) < \
                int(subset_parameter_dict["startDate"].replace("-", "")):
            raise Exception("endDate is earlier than startDate.")
        startDate_obj = datetime.datetime.strptime(subset_parameter_dict["startDate"], "%Y-%m-%d")
        endDate_obj = datetime.datetime.strptime(subset_parameter_dict["endDate"], "%Y-%m-%d")
        dateDelta_obj = endDate_obj - startDate_obj
        dateRange_obj_list = [startDate_obj + datetime.timedelta(days=x) for x in range(0, dateDelta_obj.days + 1)]
        simulation_date_list = [x.strftime("%Y%m%d") for x in dateRange_obj_list]
    else:
        simulation_date_list = [subset_parameter_dict["startDate"].replace("-", "")]
    print simulation_date_list

    # list of model configurations
    # model_configuration_list = ['analysis_assim', 'short_range', 'medium_range', 'long_range']
    model_configuration_list = [subset_parameter_dict["config"]]

    # list of model result data types
    # data_type_list = ['reservoir', 'channel', 'land', 'terrain']
    if subset_parameter_dict['geom'] == "forcing":
        data_type_list = []
    else:
        data_type_list = [subset_parameter_dict['geom'].replace("channel_rt", "channel")]

    # list of model file types
    # file_type_list = ["forecast", 'forcing']
    if subset_parameter_dict['geom'] == "forcing":
        file_type_list = ["forcing"]
    else:
        file_type_list = ["forecast"]

    # list of time stamps or model cycles
    # [1, 2, ...];  [] or None means all default time stamps
    if subset_parameter_dict['config'] == "analysis_assim":
        time_stamp_list = []
    elif subset_parameter_dict['config'] == "long_range":
        time_stamp_list = []
        if subset_parameter_dict['lag_00z'] == "on":
            time_stamp_list.append(0)
        if subset_parameter_dict['lag_06z'] == "on":
            time_stamp_list.append(6)
        if subset_parameter_dict['lag_12z'] == "on":
            time_stamp_list.append(12)
        if subset_parameter_dict['lag_18z'] == "on":
            time_stamp_list.append(18)
    else:
        time_stamp_list = [int(subset_parameter_dict['time'])]

    grid_land_dict = query_result_dict["grid_land"]
    grid_terrain_dict = query_result_dict["grid_terrain"]
    stream_comid_list = query_result_dict["stream"]["comids"]
    reservoir_comid_list = query_result_dict["reservoir"]["comids"]

    if "long_range" in model_configuration_list:
        model_configuration_list.remove("long_range")
        for i in range(1, 5):
            model_configuration_list.append("long_range_mem{0}".format(str(i)))

    output_netcdf_folder_path = os.path.join(output_folder_path, job_id)

    start_subset_nwm_netcdf_job(job_id=job_id,
                                input_netcdf_folder_path=netcdf_folder_path,
                                output_netcdf_folder_path=output_netcdf_folder_path,
                                simulation_date_list=simulation_date_list,
                                file_type_list=file_type_list,
                                model_configuration_list=model_configuration_list,
                                data_type_list=data_type_list,
                                time_stamp_list=time_stamp_list,
                                grid_land_dict=grid_land_dict,
                                grid_terrain_dict=grid_terrain_dict,
                                stream_comid_list=stream_comid_list,
                                reservoir_comid_list=reservoir_comid_list,
                                resize_dimension_grid=resize_dimension_grid,
                                resize_dimension_feature=resize_dimension_feature,
                                cleanup=cleanup,
                                include_AA_tm12=False)

    if merge_netcdfs:
        start_merge_nwm_netcdf_job(job_id=job_id,
                                   simulation_date_list=simulation_date_list,
                                   file_type_list=file_type_list,
                                   model_cfg_list=model_configuration_list,
                                   data_type_list=data_type_list,
                                   time_stamp_list=time_stamp_list,
                                   netcdf_folder_path=output_netcdf_folder_path,
                                   cleanup=cleanup)

    # zip_path = os.path.join(output_folder_path, job_id)
    # shutil.make_archive(zip_path, 'zip', output_folder_path, job_id)

    bag_save_to_path = os.path.join(output_folder_path, job_id)
    if zip_results:
        job_folder_path = bag_save_to_path
        zip_file_path = job_folder_path + '.zip'
        _zip_folder_contents(zip_file_path, job_folder_path)

        bag_save_to_path = zip_file_path
        shutil.rmtree(job_folder_path)

    return job_id, bag_save_to_path


@periodic_task(run_every=crontab())
def clean_up_subsetting_results():
    try:
        utc_current = pytz.utc.localize(datetime.datetime.utcnow())
        d_time = datetime.timedelta(minutes=-3)
        utc_expired = utc_current + d_time

        for task_i in TaskResult.objects.filter(Q(date_done__lt=utc_expired,
                                                  task_id__startswith = 'subset',
                                                  status__iexact="SUCCESS", traceback=None)):
            try:
                rslt_list = json.loads(task_i.result)
                file_path = rslt_list[1]
                if os.path.exists(file_path):
                    app_workspace.remove(file_path)
                    task_i.traceback = "Deleted on " + pytz.utc.localize(datetime.datetime.utcnow()).strftime("%Y-%m-%d %H:%M:%S %Z")
                    # Force to only update field 'traceback'
                    task_i.save(update_fields=['traceback'])
                    logger.error("Deleted celery result @ " + task_i.task_id)
            except Exception as ex:
                logger.exception("Failed to delete {0}: {1}".format(task_i.task_id, ex))
    except Exception as ex:
        logger.exception(ex)


def _zip_folder_contents(zip_file_path, source_folder_path, skip_list=[]):

    '''
    zip up all contents (files, subfolders) under source_folder_path to zip_file_path
    :param zip_file_path: path to save the resulting zip file
    :param source_folder_path: the contents of which will be zipped
    :return:
    '''

    zip_handle = zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED, allowZip64=True)
    #zip_handle = zipfile.ZipFile(zip_file_path, 'w', zipfile.ZIP_DEFLATED)
    os.chdir(source_folder_path)
    for root, dirs, files in os.walk('.'):
        for f in files:
            if f not in skip_list:
                zip_handle.write(os.path.join(root, f))

# ***----------------------------------------------------------------------------------------*** #
# ***                                                                                        *** #
# ***                                     REST API                                           *** #
# ***                                                                                        *** #
# ***----------------------------------------------------------------------------------------*** #

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

    return  conf_name + ', ' + geom_name + ' (' + var + '). ' + lag_name + mem_name + lat_name  + lon_name


def get_data_waterml(request):
    """
    Controller that will show the data in WaterML 1.1 format
	"""

    if request.GET:
        resp = get_netcdf_data(request)
        resp_dict = json.loads(resp.content)
        print resp_dict

        config = request.GET["config"]
        geom = request.GET['geom']
        var = request.GET['variable']
        if geom != 'land' and geom != "forcing":
            comid = int(request.GET['COMID'])
        else:
            comid = request.GET['COMID']
        if "lat" in request.GET:
            lat = request.GET["lat"]
        else:
            lat = ''
        if "lon" in request.GET:
            lon = request.GET["lon"]
        else:
            lon = ''
        start = request.GET["startDate"]
        if config == 'analysis_assim':
            try:
                end = request.GET["endDate"]
            except:
                end = (datetime.datetime.strptime(start, '%Y-%m-%d') + datetime.timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            end = '9999-99-99'
        if config == 'short_range' or config == 'medium_range':
            try:
                time = request.GET['time']
            except:
                time = '00'
        else:
            time = '00'

        if config == 'long_range':
            try:
                lag = request.GET['lag']
            except:
                lag = 't00z'
            try:
                member = request.GET['member']
            except:
                member = '1'
        else:
            lag = ''

        if var in ['streamflow', 'inflow', 'outflow']:
            units = {'name': 'Flow', 'short': 'cfs', 'long': 'Cubic feet per Second'}
        elif var == 'velocity':
            units = {'name': 'Velocity', 'short': 'ft/s', 'long': 'Feet per Second'}
        if var in ['SNOWH', 'SNEQV']:
            units = {'name': 'Depth', 'short': 'ft', 'long': 'Feet'}
        elif var in ['ACCET', 'ACCECAN', 'CANWAT', 'UGDRNOFF', 'SFCRNOFF']:
            units = {'name': 'Depth', 'short': 'in', 'long': 'Inches'}
        if var in ['SOILSAT_TOP', 'SOILSAT', 'FSNO']:
            units = {'name': 'Fraction', 'short': 'None', 'long': 'None'}
        elif var == 'SOIL_M':
            units = {'name': 'Soil Moisture', 'short': 'm^3/m^3', 'long': 'Water Volume per Soil Volume'}
        elif var in ['SNOWT_AVG', 'SOIL_T']:
            units = {'name': 'Temperature', 'short': 'K', 'long': 'Kelvin'}
        elif var in ['RAINRATE']:
            units = {'name': 'Rain Rate', 'short': 'in/hr', 'long': 'Millimeter per Second'}
        elif var in ['LWDOWN']:
            units = {'name': 'Surface downward long-wave radiation flux', 'short': 'W m-2', 'long': 'W m-2'}
        elif var in ['PSFC']:
            units = {'name': 'Surface Pressure', 'short': 'Pa', 'long': 'Pa'}
        elif var in ['Q2D']:
            units = {'name': '2-m Specific humidity', 'short': 'kg kg-1', 'long': 'kg kg-1'}
        elif var in ['SWDOWN']:
            units = {'name': 'Surface downward short-wave radiation flux', 'short': 'W m-2', 'long': 'W m-2'}
        elif var in ['T2D']:
            units = {'name': '2-m Air Temperature', 'short': 'K', 'long': 'K'}
        elif var in ['U2D']:
            units = {'name': '10-m U-component of wind', 'short': 'm s-1', 'long': 'm s-1'}
        elif var in ['V2D']:
            units = {'name': '10-m V-component of wind', 'short': 'm s-1', 'long': 'm s-1'}

        nodata_value = -9999

        try:
            if config != 'long_range':
                #ts = getTimeSeries(config, geom, var, comid, start, end, time)
                if "success" in resp_dict:
                    ts = json.loads(resp_dict['ts_pairs_data'])[str(comid)][1]

                    time_series = format_time_series(config, start, ts, time, nodata_value)
                    print time_series
                    site_name = get_site_name(config, geom, var, lat, lon)
                    print site_name

                    context = {
                        'config': config,
                        'comid': comid,
                        'lat': lat,
                        'lon': lon,
                        'startdate': start,
                        'site_name': site_name,
                        'units': units,
                        'time_series': time_series
                    }

                    xmlResponse = render_to_response('nwm_forecasts/waterml.xml', context)
                    xmlResponse['Content-Type'] = 'application/xml'

                    return xmlResponse
                else:
                    return Http404("Failed to retrieve wml")

            elif config == 'long_range':
                ts = getTimeSeries(config, geom, var, comid, start, end, lag, member)
                time_series = format_time_series(config, start, ts, time, nodata_value)
                site_name = get_site_name(config, geom, var, lat, lon, lag, member)

                context = {
                    'config': config,
                    'comid': comid,
                    'lat': lat,
                    'lon': lon,
                    'startdate': start,
                    'site_name': site_name,
                    'units': units,
                    'time_series': time_series
                }

                xmlResponse = render_to_response('nwm_forecasts/waterml.xml', context)
                xmlResponse['Content-Type'] = 'application/xml'

                return xmlResponse
        except Exception as e:
            print str(e)
            raise Http404('An error occurred. Please verify parameters.')


def api_page(request):

    date_string_today, date_string_minus_oldest, date_string_minus_2, date_string_minus_3 = _get_current_utc_date()

    context = {
        "date_string_today": date_string_today,
        "date_string_minus_2": date_string_minus_2,
        "date_string_minus_3": date_string_minus_3,
        "date_string_minus_oldest": date_string_minus_oldest
    }
    return render(request, 'nwm_forecasts/api_page.html', context)
