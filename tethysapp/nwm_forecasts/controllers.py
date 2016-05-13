from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render_to_response
from tethys_sdk.gizmos import SelectInput, Button

import os
import netCDF4 as nc
import json
import datetime as dt
import numpy as np

#######GLOBAL VARIABLES#########
temp_dir = None
prediction_data = None
rp_data = None
total_prediction_comids = 0
total_rp_comids = 0
sorted_prediction_comids = None
sorted_rp_comids = None
time = None
################################

@login_required()
def home(request):
    """
    Controller for the app home page.
    """

    select_input = SelectInput(display_text='Select Configuration',
                               name='config',
                               multiple=False,
                               options=[('Short Range', 'short_range'),
                                        ('Medium Range', 'medium_range'),
                                        ('Long Range', 'long_range_mem1')],
                               initial=['Short Range'],
                               original=False)

    # start = dt.datetime.today() - dt.timedelta(days=1)

    start_date = {
        'display_text': 'Choose a Beginning Date',
        'name': 'startDate',
        'autoclose': True,
        'format': 'yyyy-mm-dd',
        'start_date': '2016-05-01',
        'today_button': True,
        # 'initial': start.strftime("%Y-%m-%d")
        'initial': dt.datetime.today().strftime("%Y-%m-%d")
    }

    # end_date = {
    #     'display_text': 'Choose an Ending Date',
    #     'name': 'endDate',
    #     'autoclose': True,
    #     'format': 'yyyy-mm-dd',
    #     'start_date': '2016-05-01',
    #     'today_button': True,
    #     'initial': dt.datetime.today().strftime("%Y-%m-%d")
    # }

    submit_button = Button(display_text='Submit',
                           name='submit',
                           attributes='id="submitBtn" form=paramForm value="Success"',
                           submit=True)



    if request.GET:
        print request.GET, '###########################################'
        #Make the waterml url query string
        config = request.GET['config']
        comid = request.GET['COMID']
        lon = request.GET['longitude']
        lat = request.GET['latitude']
        startDate = request.GET['startDate']
        # time2 = '00:00:00'
        waterml_url = '?config=%s&COMID=%s&lon=%s&lat=%s&date=%s' % (config, comid, lon, lat, startDate)

        # waterML_button = Button(display_text='Get WaterML',
        #                    name='waterMLBtn',
        #                    attributes='target="_blank" href="/apps/nwm-forecasts/waterml{{waterml_url}}',
        #                    submit=False)

        HS_button = Button(display_text='Add to HydroShare',
                           name='HSBtn',
                           attributes='',
                           submit=False)

        HSGIS_button = Button(display_text='Add to HydroShare GIS',
                              name='HSGISBtn',
                              attributes='',
                              submit=False)

        context = {
            'select_input': select_input,
            'start_date': start_date,
            # 'end_date': end_date,
            'submit_button': submit_button,
            # 'waterML_button': waterML_button,
            'HS_button': HS_button,
            'HSGIS_button': HSGIS_button,
            'waterml_url': waterml_url
        }

        return render(request, 'nwm_forecasts/home.html', context)

    else:
        context = {
            'select_input': select_input,
            'start_date': start_date,
            # 'end_date': end_date,
            'submit_button': submit_button
        }
        return render(request, 'nwm_forecasts/home.html', context)


def get_netcdf_data(request):
    if request.method == 'GET':
        get_data = request.GET
        ts_pairs_data = {}  # For time series pairs data
        rp_cls_data = {}  # For return period classification data

        try:
            config = get_data['config']
            comid = int(get_data['comid'])
            startDate = get_data['startDate']

            app_dir = os.path.dirname(__file__)
            dateDir = ''.join(['nwm.', startDate.replace('-', '')])
            localFileDir = os.path.join(app_dir, 'data', dateDir, config)
            nc_files = sorted([x for x in os.listdir(localFileDir) if 'channel_rt' in x and 'georeferenced' not in x])
            print nc_files

            # ***----------------------------------------------------------------------------------------------*** #
            # *** This part needs to be modified so it takes a start date and time to calculate the local path *** #
            # ***----------------------------------------------------------------------------------------------*** #

            local_file_path = os.path.join(localFileDir, nc_files[0])
            prediction_data = nc.Dataset(local_file_path, mode="r")

            qout_dimensions = prediction_data.variables['station_id'].dimensions

            if qout_dimensions[0] == 'station':
                comidList = prediction_data.variables['station_id'][:]
                comidIndex = int(np.where(comidList == comid)[0])
            else:
                return JsonResponse({'error': "Invalid netCDF file"})

            variables = prediction_data.variables.keys()
            print variables, '******************'
            if 'time' in variables:
                time = [int(nc.num2date(0, prediction_data.variables['time'].units).strftime('%s'))]
            else:
                return JsonResponse({'error': "Invalid netCDF file"})

            q_out = []
            for ncf in nc_files:
                local_file_path = os.path.join(localFileDir, ncf)
                prediction_dataTemp = nc.Dataset(local_file_path, mode="r")
                q_outT = prediction_dataTemp.variables['streamflow'][comidIndex].tolist()
                print q_outT
                q_out.append(round(q_outT, 6))

            ts_pairs_data[str(comid)] = [time, q_out]

            return JsonResponse({
                "success": "Data analysis complete!",
                "ts_pairs_data": json.dumps(ts_pairs_data)
            })

        except Exception as e:
            print str(e)
            return JsonResponse({'error': 'No data found for the selected reach.'})
    else:
        return JsonResponse({'error': "Bad request. Must be a GET request."})


# ***----------------------------------------------------------------------------------------*** #
# ***                                                                                        *** #
# ***                                     REST API                                           *** #
# ***                                                                                        *** #
# ***----------------------------------------------------------------------------------------*** #

def getTimeSeries(beginDate):
    nDays = 15 # (endDate - beginDate).days
    datelist = [dt.datetime.strptime(beginDate, "%Y-%m-%d") + dt.timedelta(days=x) for x in range(0,nDays)]

    ts = [range(0,16)]
    # for d in datelist:
    #
    #     ts.append()
    return ts


def format_time_series(startDate, ts, nodata_value):
    nDays = len(ts)
    datelist = [dt.datetime.strptime(startDate, "%Y-%m-%d") + dt.timedelta(days=x) for x in range(0,nDays)]
    formatted_ts = []
    for i in range(0, nDays):
        formatted_val = ts[i]
        if (formatted_val is None):
            formatted_val = nodata_value
        formatted_date = datelist[i].strftime('%Y-%m-%dT%H:%M:%S')
        formatted_ts.append({'date':formatted_date, 'val':formatted_val})

    return formatted_ts


def get_site_name(lat, lon):
    lat_name = "Lat: %s" % lat
    lon_name = "Lon: %s" % lon


    return lat_name + ' ' +  lon_name


def get_data_waterml(request):
    """
	Controller that will show the data in WaterML 1.1 format
	"""
    if request.GET:
        config = request.GET["config"]
        comid = request.GET["COMID"]
        lat = request.GET["lat"]
        lon = request.GET["lon"]
        start = request.GET["date"]

        nodata_value = -9999
        ts = getTimeSeries(start)
        time_series = format_time_series(start, ts, nodata_value)
        site_name = get_site_name(float(lat), float(lon))
        context = {
            'config': config,
            'comid': comid,
            'lat': lat,
            'lon': lon,
            'startdate': start,
            'site_name': site_name,
            'time_series': time_series
        }

        xmlResponse = render_to_response('nwm_forecasts/waterml.xml', context)
        xmlResponse['Content-Type'] = 'application/xml'
        xmlResponse['content-disposition'] = "attachment; filename=output-time-series.xml"
        return xmlResponse