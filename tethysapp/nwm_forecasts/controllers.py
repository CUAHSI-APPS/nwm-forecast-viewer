from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404, FileResponse
from django.shortcuts import render_to_response
from tethys_sdk.gizmos import SelectInput, ToggleSwitch, Button, DatePicker
from django.conf import settings
from hs_restclient import HydroShare, HydroShareAuthOAuth2, HydroShareNotAuthorized, HydroShareNotFound
from subset_nwm_netcdf.query import _project_shapely_geom

hydroshare_ready = True

try:
    from tethys_services.backends.hs_restclient_helper import get_oauth_hs
except Exception:
    print "could not load: tethys_services.backends.hs_restclient_helper import get_oauth_hs"
    hydroshare_ready = False


import os
import shutil
import re
import netCDF4 as nc
import json
import datetime as dt
import numpy as np
import tempfile
import xmltodict
import shapely.geometry
import fiona
import pycrs
import pyproj
import geojson

hs_hostname = 'www.hydroshare.org'
app_dir = '/projects/water/nwm/data/'
transition_date_v11 = "20170508"
transition_timestamp_v11_AA = "12"
transition_timestamp_v11_SR = "11"
transition_timestamp_v11_MR = "12"
transition_timestamp_v11_LR = "00"

@login_required()
def home(request):
    """
    Controller for the app home page.
    """

    config_input = SelectInput(display_text='Enter Configuration',
                               name='config',
                               multiple=False,
                               options=[('Analysis and Assimilation', 'analysis_assim'),
                                        ('Short Range', 'short_range'),
                                        ('Medium Range', 'medium_range'),
                                        ('Long Range', 'long_range')],
                               initial=['Short Range'],
                               original=True)

    geom_input = SelectInput(display_text='Enter Geometry',
                             name='geom',
                             multiple=False,
                             options=[('Channel', 'channel_rt'),
                                      ('Land', 'land'),
                                      ('Reservoir', 'reservoir'),
                                      ('Forcing', 'forcing')],
                             initial=['Channel'],
                             original=True)


    start_date = DatePicker(name='startDate',
                            display_text='Enter Beginning Date',
                            end_date='0d',
                            autoclose=True,
                            format='yyyy-mm-dd',
                            start_date='2016-05-01',
                            today_button=True,
                            initial=dt.datetime.utcnow().strftime("%Y-%m-%d"))

    end_date = DatePicker(name='endDate',
                          end_date='0d',
                          autoclose=True,
                          format='yyyy-mm-dd',
                          start_date='2016-05-01',
                          today_button=True,
                          initial=dt.datetime.utcnow().strftime("%Y-%m-%d"),
                          classes="hidden")

    start_time = SelectInput(display_text='Enter Initialization Time (UTC)',
                             name='time',
                             multiple=False,
                             options=[('00:00', '00'), ('01:00', '01'),
                                      ('02:00', '02'), ('03:00', '03'),
                                      ('04:00', '04'), ('05:00', '05'),
                                      ('06:00', '06'), ('07:00', '07'),
                                      ('08:00', '08'), ('09:00', '09'),
                                      ('10:00', '10'), ('11:00', '11'),
                                      ('12:00', '12'), ('13:00', '13'),
                                      ('14:00', '14'), ('15:00', '15'),
                                      ('16:00', '16'), ('17:00', '17'),
                                      ('18:00', '18'), ('19:00', '19'),
                                      ('20:00', '20'), ('21:00', '21'),
                                      ('22:00', '22'), ('23:00', '23')],
                             initial=['00:00'],
                             original=True)

    longRangeLag00 = ToggleSwitch(display_text='', name='00z', size='mini', initial=True)
    longRangeLag06 = ToggleSwitch(display_text='', name='06z', size='mini')
    longRangeLag12 = ToggleSwitch(display_text='', name='12z', size='mini')
    longRangeLag18 = ToggleSwitch(display_text='', name='18z', size='mini')

    submit_button = Button(display_text='Submit',
                           name='submit',
                           attributes='id="submitBtn" form=paramForm value="Success"',
                           submit=True)

    if request.GET:
        # Make the waterml url query string
        config = request.GET['config']
        if config == "medium_range":
            start_time = SelectInput(display_text='Enter Initialization Time (UTC)',
                                     name='time',
                                     multiple=False,
                                     options=[('00:00', '00'),
                                              ('06:00', '06'),
                                              ('12:00', '12'),
                                              ('18:00', '18')],
                                     initial=['00:00'],
                                     original=True)

        geom = request.GET['geom']
        variable = request.GET['variable']
        if geom != 'land' and geom != 'forcing':
            comid = request.GET['COMID']
        else:
            comid = ','.join([request.GET['Y'], request.GET['X']])
        lon = request.GET['longitude']
        lat = request.GET['latitude']
        startDate = request.GET['startDate']
        endDate = request.GET['endDate']
        time = request.GET['time']

        lagList = []
        if '00z' in request.GET:
            lagList.append('t00z')
        if '06z' in request.GET:
            lagList.append('t06z')
        if '12z' in request.GET:
            lagList.append('t12z')
        if'18z' in request.GET:
            lagList.append('t18z')

        lag = ','.join(lagList)
        waterml_url = '?config=%s&geom=%s&variable=%s&COMID=%s&lon=%s&lat=%s&startDate=%s&endDate=%s&time=%s&lag=%s' % \
                      (config, geom, variable, comid, lon, lat, startDate, endDate, time, lag)

        context = {
            'config_input': config_input,
            'geom_input': geom_input,
            'start_date': start_date,
            'end_date': end_date,
            'start_time': start_time,
            'longRangeLag00': longRangeLag00,
            'longRangeLag06': longRangeLag06,
            'longRangeLag12': longRangeLag12,
            'longRangeLag18': longRangeLag18,
            'submit_button': submit_button,
            'waterml_url': waterml_url,
            'hs_ready': hydroshare_ready,
            'watershed_geojson_str': request.session.get("watershed_geojson_str", "")
        }

        return render(request, 'nwm_forecasts/home.html', context)

    else:
        if 'watershed_geojson_str' in request.session:
            del request.session['watershed_geojson_str']
            request.session.modified = True

        context = {
            'config_input': config_input,
            'geom_input': geom_input,
            'start_date': start_date,
            'start_time': start_time,
            'end_date': end_date,
            'longRangeLag00': longRangeLag00,
            'longRangeLag06': longRangeLag06,
            'longRangeLag12': longRangeLag12,
            'longRangeLag18': longRangeLag18,
            'submit_button': submit_button,
            'hs_ready': hydroshare_ready,
            'watershed_geojson_str': ""
        }
        return render(request, 'nwm_forecasts/home.html', context)


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
            time = get_data['time']
            timeCheck = ''.join(['t', time, 'z'])
            lag = get_data['lag'].split(',')

            if config == 'short_range' or config == 'medium_range':

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
                # localFileDir = os.path.join(app_dir, config)

                if geom == "forcing":
                    localFileDir_v10 = os.path.join(app_dir, "fe_analysis_assim")
                    localFileDir_v11 = os.path.join(app_dir, "forcing_analysis_assim")
                    #localFileDir_v11 = os.path.join(app_dir, "fe_analysis_assim")
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
                    v10_data = processNCFiles(localFileDir_v10, nc_files_v10, geom, comid, var, version="v1.0")
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
                q_out_group = []
                for lg in lag:
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


def processNCFiles(localFileDir, nc_files, geom, comid, var, version="v1.1"):
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
    else:
        return JsonResponse({'error': "Invalid netCDF file"})
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
        elif var in ['RAINRATE']:
            q_outT = prediction_dataTemp.variables[var][0, comidIndexY, comidIndexX].tolist()
            q_out.append(q_outT)
    return q_out


def get_hs_watershed_list(request):
    response_obj = {}
    try:
        if request.is_ajax() and request.method == 'GET':
            resources_list = []
            hs = get_oauth_hs(request)
            if hs is None:
                response_obj['error'] = 'You must be signed in through HydroShare to access this feature. ' \
                                        'Please log out and then sign in again using your HydroShare account.'
            else:
                creator = None
                try:
                    creator = hs.getUserInfo()['username']
                except Exception:
                    pass

                # loop through all Generic and Feature res current user owns
                valid_res_types = ['GenericResource', 'GeographicFeatureResource']

                for resource in hs.getResourceList(types=valid_res_types, creator=creator):
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
                        print ex.message
                        print "Failed res in get_hs_watershed_list: " + str(resource)

                resources_json = json.dumps(resources_list)

                response_obj['success'] = 'Resources obtained successfully.'
                response_obj['resources'] = resources_json

    except Exception as ex:
        print ex
        response_obj = {"error": "Failed to load resources from HydroShare. Did you sign in with your HydroShare account?"}
    finally:
        return JsonResponse(response_obj)


def load_watershed(request):

    if request.is_ajax() and request.method == 'GET':
        res_id = str(request.GET['res_id'])
        filename = str(request.GET['filename'])
        response_obj = get_geojson_from_hs_resource(res_id, filename, request)
        return JsonResponse(response_obj)


def get_geojson_from_hs_resource(res_id, filename, request):

    response_obj = {}
    try:
        hs = get_oauth_hs(request)

        if filename.endswith('.geojson'):
            # geojson file
            geojson_str = str(hs.getResourceFile(pid=res_id, filename=filename).next())
            geojson_obj = geojson.loads(geojson_str)
            geojson_geom_first = geojson_obj
            if geojson_obj.type.lower() == "featurecollection":
                geojson_geom_first = geojson_obj.features[0].geometry
            shape_obj = shapely.geometry.asShape(geojson_geom_first)
            in_pyproj_obj = pyproj.Proj(init='epsg:4326')
            response_obj['type'] = 'geojson'

        elif filename.endswith('.shp'):
            proj_str_raw = str(hs.getResourceFile(pid=res_id, filename=filename.replace('.shp', '.prj')).next())

            proj_str = proj_str_raw.replace('\n', '')
            response_obj['type'] = 'shp'

            fromcrs = pycrs.parser.from_unknown_text(proj_str)
            fromcrs_proj4 = fromcrs.to_proj4()
            in_pyproj_obj = pyproj.Proj(fromcrs_proj4)

            tmp_dir = tempfile.mkdtemp()
            for ext in [".prj", ".dbf", ".shx", ".shp"]:
                fn = filename.replace(".shp", ext)
                shp_path = os.path.join(tmp_dir, fn)
                with open(shp_path, "wb+") as shp:
                    for chunk in hs.getResourceFile(pid=res_id, filename=fn):
                        shp.write(chunk)

            shp_obj = fiona.open(shp_path)
            first_feature_obj = next(shp_obj)
            shape_obj = shapely.geometry.shape(first_feature_obj["geometry"])
            shutil.rmtree(tmp_dir)

        if shape_obj.geom_type.lower() == "multipolygon":
            polygon_exterior_linearring = shape_obj[0].exterior
        elif shape_obj.geom_type.lower() == "polygon":
            polygon_exterior_linearring = shape_obj.exterior
        else:
            raise Exception("Input Geometry is not Polygon")

        polygon_exterior_linearring_shape_obj = shapely.geometry.Polygon(polygon_exterior_linearring)

        out_pyproj_obj = pyproj.Proj(init='epsg:3857')
        polygon_exterior_linearring_shape_obj_3857 = \
            _project_shapely_geom(in_geom_obj=polygon_exterior_linearring_shape_obj,
                                  in_proj_type="pyproj",
                                  in_proj_value=in_pyproj_obj,
                                  out_proj_type="pyproj",
                                  out_proj_value=out_pyproj_obj)

        #geojson_str = json.dumps({"type": "FeatureCollection", "features": [{"type": "Feature", "geometry": shapely.geometry.mapping(polygon_query_window), "properties":{}}]})

        # covert "geometry" part of this polygon to geojson
        geojson_str = json.dumps(shapely.geometry.mapping(polygon_exterior_linearring_shape_obj_3857))
        session_key = "watershed_geojson_str"
        if session_key in request.session:
            del request.session[session_key]
        request.session[session_key] = geojson_str
        request.session.modified = True

        response_obj['success'] = 'Geojson obtained successfully.'
        response_obj['geojson_str'] = geojson_str
        response_obj['id'] = '%s:%s' % (res_id, filename)

    except Exception as e:
        print e
        response_obj['error'] = 'Failed to load watershed.'

    return response_obj


@login_required()
def upload_to_hydroshare(request):
    temp_dir = None
    try:
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

from django.views.decorators.csrf import csrf_exempt

@csrf_exempt
def subset_watershed(request):

    if request.method == 'POST':
        request_json = json.loads(request.body)
        try:
            print request_json
            import os
            import logging
            import uuid
            import datetime
            from subset_nwm_netcdf.query import query_comids_and_grid_indices
            from subset_nwm_netcdf.subset import start_subset_nwm_netcdf_job
            from subset_nwm_netcdf.merge import start_merge_nwm_netcdf_job

            db_file_path = "/nwm.sqlite"
            job_id = str(uuid.uuid4())
            logger = logging.getLogger()

            all_start_dt = datetime.datetime.now()
            logger.info("-------------Process Started-------------------")
            logger.info(all_start_dt)

            # geojson example
            query_type = "geojson"
            shp_path = None
            geom_str = request_json['geometry']
            print geom_str
            in_epsg = 3857  # NAD83; epsg is required
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
            print query_result_dict

            netcdf_folder_path = "/projects/water/nwm/data/nomads/"

            # Path of output folder
            output_folder_path = "/tmp"

            # shrink dimension size to cover subsetting domain only
            resize_dimension_grid = True
            resize_dimension_feature = True
            # merge resulting netcdfs
            merge_netcdfs = False
            # remove intermediate files
            cleanup = True

            # list of simulation dates
            simulation_date_list = ["20170509"]

            # list of model file types
            #file_type_list = ["forecast", 'forcing']
            file_type_list = ["forcing"]

            # list of model configurations
            #model_configuration_list = ['analysis_assim', 'short_range', 'medium_range', 'long_range']
            model_configuration_list = ['analysis_assim']

            # list of model result data types
            #data_type_list = ['reservoir', 'channel', 'land', 'terrain']
            data_type_list = ['channel']

            # list of time stamps or model cycles
            # [1, 2, ...];  [] or None means all default time stamps
            time_stamp_list = []

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
                                        cleanup=cleanup)
            import shutil

            zip_path = os.path.join(output_folder_path, job_id)
            shutil.make_archive(zip_path, 'zip', os.path.join(output_folder_path, job_id))

            bag_save_to_path = zip_path + ".zip"
            response = FileResponse(open(bag_save_to_path, 'rb'), content_type='application/zip')
            response['Content-Disposition'] = 'attachment; filename="' + 'ABC123.zip"'
            response['Content-Length'] = os.path.getsize(bag_save_to_path)
            return response
        except Exception as ex:
            print ex


    pass


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
        datelist = [dt.datetime.strptime(startDate, "%Y-%m-%d") + dt.timedelta(hours=x + int(time) +1) for x in range(0,nDays)]
    elif config == 'medium_range':
        datelist = [dt.datetime.strptime(startDate, "%Y-%m-%d") + dt.timedelta(hours=x+9) for x in range(0, nDays*3, 3)]
    elif config == 'analysis_assim':
        datelist = [dt.datetime.strptime(startDate, "%Y-%m-%d") + dt.timedelta(hours=x) for x in range(0, nDays)]
    elif config == 'long_range':
        datelist = [dt.datetime.strptime(startDate, "%Y-%m-%d") + dt.timedelta(hours=x + 6) for x in range(0, nDays*6, 6)]

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
        if geom != 'land':
            comid = int(request.GET['COMID'])
        else:
            comid = request.GET['COMID']
        if "lat=" in request.GET:
            lat = request.GET["lat"]
        else:
            lat = ''
        if "lon=" in request.GET:
            lon = request.GET["lon"]
        else:
            lon = ''
        start = request.GET["startDate"]
        if config == 'analysis_assim':
            try:
                end = request.GET["endDate"]
            except:
                end = (dt.datetime.strptime(start, '%Y-%m-%d') + dt.timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            end = '9999-99-99'
        if config == 'short_range':
            try:
                time = request.GET['time']
            except:
                time = '00'
        elif config == 'medium_range':
            time = '06'
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
        if var in ['SNOWT_AVG', 'SOIL_T']:
            units = {'name': 'Temperature', 'short': 'K', 'long': 'Kelvin'}

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
