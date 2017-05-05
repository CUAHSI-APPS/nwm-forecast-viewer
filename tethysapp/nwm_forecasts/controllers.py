from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, Http404
from django.shortcuts import render_to_response
from tethys_sdk.gizmos import SelectInput, ToggleSwitch, Button, DatePicker
from django.conf import settings
from hs_restclient import HydroShare, HydroShareAuthOAuth2, HydroShareNotAuthorized, HydroShareNotFound

import os
import datetime
import netCDF4 as nc
import json
import datetime as dt
import numpy as np
import shapefile
import tempfile

hs_hostname = 'www.hydroshare.org'
app_dir = '/projects/water/nwm/data/'
transition_date_v11 = "20170503"

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
                                      ('Reservoir', 'reservoir')],
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
        if geom != 'land':
            comid = request.GET['COMID']
        else:
            comid = ','.join([request.GET['Y'], request.GET['X']])
        lon = request.GET['longitude']
        lat = request.GET['latitude']
        startDate = request.GET['startDate']
        endDate = request.GET['endDate']
        time = request.GET['time']

        watershed_obj = None
        if request.GET.get('watershed'):
            watershed = request.GET['watershed']
            args = watershed.split(':')
            watershed_obj = get_geojson_from_hs_resource(args[0], args[1], request)

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
            'watershed': watershed_obj
        }

        return render(request, 'nwm_forecasts/home.html', context)

    else:
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
            'submit_button': submit_button
        }
        return render(request, 'nwm_forecasts/home.html', context)


def get_netcdf_data(request):
    if request.method == 'GET':
        get_data = request.GET
        ts_pairs_data = {}

        try:
            config = get_data['config']
            geom = get_data['geom']
            var = get_data['variable']
            if geom != 'land':
                comid = int(get_data['comid'])
            else:
                comid = get_data['comid']
            startDate = get_data['startDate']
            time = get_data['time']
            lag = get_data['lag'].split(',')

            if config == 'short_range' or config == 'medium_range':

                timeCheck = ''.join(['t', time, 'z'])

                dateDir = startDate.replace('-', '')
                localFileDir = os.path.join(app_dir, config, dateDir)

                if int(dateDir) < int(transition_date_v11):
                    # v1.0
                    nc_files = sorted([x for x in os.listdir(localFileDir) if geom in x and timeCheck in x
                                    and "georeferenced" in x])
                    ts_pairs_data[str(comid)] = processNCFiles(localFileDir, nc_files, geom, comid, var, version="v1.0")
                else:
                    # v1.1
                    nc_files = sorted([x for x in os.listdir(localFileDir) if geom in x and timeCheck in x
                                       and "georeferenced" not in x])
                    ts_pairs_data[str(comid)] = processNCFiles(localFileDir, nc_files, geom, comid, var)

                return JsonResponse({
                    "success": "Data analysis complete!",
                    "ts_pairs_data": json.dumps(ts_pairs_data)
                })

            elif config == 'analysis_assim':

                endDate = get_data['endDate'].replace('-', '')
                endDate_obj = datetime.datetime.strptime(endDate + " UTC", '%Y%m%d %Z')
                endDate_obj = endDate_obj + datetime.timedelta(days=1)
                endDate = endDate_obj.strftime("%Y%m%d")

                dateDir = startDate.replace('-', '')
                localFileDir = os.path.join(app_dir, config)


                nc_files_v10 = sorted([x for x in os.listdir(localFileDir) if geom in x
                                       and int(x.split('.')[1]) >= int(dateDir)
                                       and int(x.split('.')[1]) < min(int(transition_date_v11), int(endDate))
                                       and 'tm00' in x
                                       and "georeferenced" in x])

                nc_files_v11 = sorted([x for x in os.listdir(localFileDir) if geom in x
                                       and int(x.split('.')[1]) >= max(int(dateDir), int(transition_date_v11))
                                       and int(x.split('.')[1]) < int(endDate)
                                       and 'tm00' in x
                                       and "georeferenced" not in x])
                start_time = None
                q_list = []
                if len(nc_files_v10) > 0:
                    v10_data = processNCFiles(localFileDir, nc_files_v10, geom, comid, var, version="v1.0")
                    start_time = v10_data[0]
                    q_list = v10_data[1]

                if len(nc_files_v11) > 0:
                    v11_data = processNCFiles(localFileDir, nc_files_v11, geom, comid, var)
                    if start_time is None:
                        start_time = v11_data[0]
                    q_list = q_list + v11_data[1]

                ts_pairs_data[str(comid)] = [start_time, q_list, "notLong"]
                # ts_pairs_data[str(comid)] = processNCFiles(localFileDir, nc_files, geom, comid, var)

                return JsonResponse({
                    "success": "Data analysis complete!",
                    "ts_pairs_data": json.dumps(ts_pairs_data)
                })

            elif config == 'long_range':
                q_out_group = []
                for lg in lag:
                    timeCheck = ''.join(['t', lg])

                    dateDir = startDate.replace('-', '')
                    localFileDir = os.path.join(app_dir, config, dateDir)

                    q_out_1 = []; q_out_2 = []; q_out_3 = []; q_out_4 = []
                    if geom == 'channel_rt':

                        nc_files_1 = sorted([x for x in os.listdir(localFileDir) if
                                             'channel_rt_1' in x and timeCheck in x
                                             and "georeferenced" not in x])
                        nc_files_2 = sorted([x for x in os.listdir(localFileDir) if
                                             'channel_rt_2' in x and timeCheck in x
                                             and "georeferenced" not in x])
                        nc_files_3 = sorted([x for x in os.listdir(localFileDir) if
                                             'channel_rt_3' in x and timeCheck in x
                                             and "georeferenced" not in x])
                        nc_files_4 = sorted([x for x in os.listdir(localFileDir) if
                                             'channel_rt_4' in x and timeCheck in x
                                             and "georeferenced" not in x])

                        local_file_path = os.path.join(localFileDir, nc_files_1[0])
                        prediction_data = nc.Dataset(local_file_path, mode="r")

                        comidList = prediction_data.variables['feature_id'][:]
                        comidIndex = int(np.where(comidList == comid)[0])

                        loopThroughFiles(localFileDir, q_out_1, nc_files_1, var, comidIndex)
                        loopThroughFiles(localFileDir, q_out_2, nc_files_2, var, comidIndex)
                        loopThroughFiles(localFileDir, q_out_3, nc_files_3, var, comidIndex)
                        loopThroughFiles(localFileDir, q_out_4, nc_files_4, var, comidIndex)

                    elif geom == 'reservoir':
                        nc_files_1 = sorted([x for x in os.listdir(localFileDir) if
                                             'reservoir_1' in x and timeCheck in x
                                             and "georeferenced" not in x])
                        nc_files_2 = sorted([x for x in os.listdir(localFileDir) if
                                             'reservoir_2' in x and timeCheck in x
                                             and "georeferenced" not in x])
                        nc_files_3 = sorted([x for x in os.listdir(localFileDir) if
                                             'reservoir_3' in x and timeCheck in x
                                             and "georeferenced" not in x])
                        nc_files_4 = sorted([x for x in os.listdir(localFileDir) if
                                             'reservoir_4' in x and timeCheck in x
                                             and "georeferenced" not in x])

                        local_file_path = os.path.join(localFileDir, nc_files_1[0])
                        prediction_data = nc.Dataset(local_file_path, mode="r")

                        comidList = prediction_data.variables['feature_id'][:]
                        comidIndex = int(np.where(comidList == comid)[0])

                        loopThroughFiles(localFileDir, q_out_1, nc_files_1, var, comidIndex)
                        loopThroughFiles(localFileDir, q_out_2, nc_files_2, var, comidIndex)
                        loopThroughFiles(localFileDir, q_out_3, nc_files_3, var, comidIndex)
                        loopThroughFiles(localFileDir, q_out_4, nc_files_4, var, comidIndex)

                    elif geom == 'land':
                        nc_files_1 = sorted([x for x in os.listdir(localFileDir) if
                                             'land_1' in x and timeCheck in x
                                             and "georeferenced" not in x])
                        nc_files_2 = sorted([x for x in os.listdir(localFileDir) if
                                             'land_2' in x and timeCheck in x
                                             and "georeferenced" not in x])
                        nc_files_3 = sorted([x for x in os.listdir(localFileDir) if
                                             'land_3' in x and timeCheck in x
                                             and "georeferenced" not in x])
                        nc_files_4 = sorted([x for x in os.listdir(localFileDir) if
                                             'land_4' in x and timeCheck in x
                                             and "georeferenced" not in x])

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
    elif geom == 'land':
        comidList = comid.split(',')
        comidIndexY = int(comidList[0])
        comidIndexX = int(comidList[1])
        loopThroughFiles(localFileDir, q_out, nc_files, var, None, comidIndexY, comidIndexX)
    else:
        return JsonResponse({'error': "Invalid netCDF file"})

    print "comid index: {0}".format(comidIndex)

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
    return q_out


def get_hs_watershed_list(request):
    response_obj = {}
    if request.is_ajax() and request.method == 'GET':
        resources_list = []
        hs = get_hs_object(request)
        if hs is None:
            response_obj['error'] = 'You must be signed in through HydroShare to access this feature. ' \
                                    'Please log out and then sign in again using your HydroShare account.'
        else:
            creator = None
            try:
                creator = hs.getUserInfo()['username']
            except Exception:
                pass

            valid_res_types = ['GenericResource', 'GeographicFeatureResource']
            valid_file_extensions = ['.shp', '.geojson']

            for resource in hs.getResourceList(types=valid_res_types, creator=creator):
                res_id = resource['resource_id']
                try:
                    for res_file in hs.getResourceFileList(res_id):
                        filename = os.path.basename(res_file['url'])
                        if os.path.splitext(filename)[1] in valid_file_extensions:
                            resources_list.append({
                                'title': resource['resource_title'],
                                'id': res_id,
                                'owner': resource['creator'],
                                'filename': filename
                            })
                            break
                except Exception as e:
                    print str(e)
                    continue

            resources_json = json.dumps(resources_list)

            response_obj['success'] = 'Resources obtained successfully.'
            response_obj['resources'] = resources_json

        return JsonResponse(response_obj)


def get_hs_object(request):
    try:
        hs = get_oauth_hs(request)
    except Exception as e:
        print str(e)
        hs = None
    return hs


def get_oauth_hs(request):
    global hs_hostname

    client_id = getattr(settings, 'SOCIAL_AUTH_HYDROSHARE_KEY', 'None')
    client_secret = getattr(settings, 'SOCIAL_AUTH_HYDROSHARE_SECRET', 'None')

    # Throws django.core.exceptions.ObjectDoesNotExist if current user is not signed in via HydroShare OAuth
    token = request.user.social_auth.get(provider='hydroshare').extra_data['token_dict']
    auth = HydroShareAuthOAuth2(client_id, client_secret, token=token)

    return HydroShare(auth=auth, hostname=hs_hostname, use_https=True)


def load_watershed(request):
    geojson_str = None

    if request.is_ajax() and request.method == 'GET':
        res_id = str(request.GET['res_id'])
        filename = str(request.GET['filename'])
        response_obj = get_geojson_from_hs_resource(res_id, filename, request)
        return JsonResponse(response_obj)


def get_geojson_from_hs_resource(res_id, filename, request):
    response_obj = {}
    try:
        hs = get_hs_object(request)

        if filename.endswith('.geojson'):
            geojson_str = str(hs.getResourceFile(pid=res_id, filename=filename).next())

            response_obj['type'] = 'geojson'

        elif filename.endswith('.shp'):
            proj_str_raw = str(hs.getResourceFile(pid=res_id, filename=filename.replace('.shp', '.prj')).next())
            proj_str = json.dumps(proj_str_raw)
            proj_str.replace('\n', '')
            response_obj['proj_str'] = proj_str

            '''
            Credit: The following code was adapted from https://gist.github.com/frankrowe/6071443
            '''
            # Read the shapefile-like object
            with tempfile.TemporaryFile() as f1:
                for chunk in hs.getResourceFile(pid=res_id, filename=filename):
                    f1.write(chunk)
                with tempfile.TemporaryFile() as f2:
                    for chunk in hs.getResourceFile(pid=res_id, filename=filename.replace('.shp', '.dbf')):
                        f2.write(chunk)

                    shp_reader = shapefile.Reader(shp=f1, dbf=f2)
                    fields = shp_reader.fields[1:]
                    field_names = [field[0] for field in fields]
                    shp_buffer = []
                    for sr in shp_reader.shapeRecords():
                        atr = dict(zip(field_names, sr.record))
                        geom = sr.shape.__geo_interface__
                        shp_buffer.append(dict(type="Feature", geometry=geom, properties=atr))

            # Write the GeoJSON object
            geojson_str = json.dumps({"type": "FeatureCollection", "features": shp_buffer})
            '''
            End credit
            '''

            response_obj['proj_str'] = proj_str

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

            res_id = None
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
                ts = getTimeSeries(config, geom, var, comid, start, end, time)
                time_series = format_time_series(config, start, ts, time, nodata_value)
                site_name = get_site_name(config, geom, var, lat, lon)

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
