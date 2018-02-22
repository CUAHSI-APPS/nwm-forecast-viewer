import json
import time
import logging
import uuid
import os
import datetime

from django.http import JsonResponse, HttpResponse, FileResponse, Http404
from django.shortcuts import render_to_response

from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes

from .subset_utilities import _do_spatial_query, _perform_subset, _check_latest_data
from .timeseries_utilities import format_time_series, get_site_name, getTimeSeries
from .controllers_ajax import get_netcdf_data


logger = logging.getLogger(__name__)


@api_view(['GET'])
@authentication_classes((TokenAuthentication, SessionAuthentication))
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
        elif var in ['FSNO']:
            units = {'name': 'km^2/km^2', 'short': 'Snow cover', 'long': 'Snow cover'}
        elif var in ['SOILSAT_TOP', 'SOILSAT']:
            units = {'name': 'm^3/m^3', 'short': 'Soil Saturation', 'long': 'Soil Saturation'}
        elif var == 'SOIL_M':
            units = {'name': 'Soil Moisture', 'short': 'm^3/m^3', 'long': 'Water Volume per Soil Volume'}
        elif var in ['SNOWT_AVG', 'SOIL_T']:
            units = {'name': 'Temperature', 'short': 'K', 'long': 'Kelvin'}
        elif var in ['RAINRATE']:
            units = {'name': 'Rain Rate', 'short': 'in/hr', 'long': 'Millimeter per Second'}
        elif var in ['LWDOWN']:
            units = {'name': 'Surface downward long-wave radiation flux', 'short': 'W/m^2', 'long': 'W/m^2'}
        elif var in ['PSFC']:
            units = {'name': 'Surface Pressure', 'short': 'Pa', 'long': 'Pa'}
        elif var in ['Q2D']:
            units = {'name': '2-m Specific humidity', 'short': 'kg/kg', 'long': 'kg/kg'}
        elif var in ['SWDOWN']:
            units = {'name': 'Surface downward short-wave radiation flux', 'short': 'W/m^2', 'long': 'W/m^2'}
        elif var in ['T2D']:
            units = {'name': '2-m Air Temperature', 'short': 'K', 'long': 'K'}
        elif var in ['U2D']:
            units = {'name': '10-m U-component of wind', 'short': 'm/s', 'long': 'm/s'}
        elif var in ['V2D']:
            units = {'name': '10-m V-component of wind', 'short': 'm/s', 'long': 'm/s'}

        nodata_value = -9999

        try:
            if config != 'long_range':
                # ts = getTimeSeries(config, geom, var, comid, start, end, time)
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


@api_view(['POST'])
@authentication_classes((TokenAuthentication, SessionAuthentication))
def spatial_query_api(request):
    try:
        request_dict = json.loads(request.body)
        watershed_geometry = request_dict['watershed_geometry']
        watershed_epsg = int(request_dict['watershed_epsg'])
        start = time.time()
        query_result_dict = _do_spatial_query(watershed_geometry, watershed_epsg)
        end = time.time()
        result_dict = {"time_elapsed": end-start}
        if query_result_dict:
            result_dict.update(query_result_dict)
        response = JsonResponse(result_dict)
        return response
    except Exception as ex:
        logger.error("------ERROR: subset_watershed_api--------")
        logger.exception(ex.message)
        return HttpResponse(status=500, content=ex.message)


@api_view(['POST'])
@authentication_classes((TokenAuthentication, SessionAuthentication))
def subset_watershed_api(request):
    try:
        request_dict = json.loads(request.body)
        watershed_geometry = request_dict['watershed_geometry']
        watershed_epsg = int(request_dict['watershed_epsg'])
        spatial_query_only = request_dict.get('query_only', 'False')
        if str(spatial_query_only).lower() == "true":
            spatial_query_only = True
        else:
            spatial_query_only = False
        subset_parameter_dict = request_dict.get('subset_parameter', None)

        logger.info("------START: subset_watershed_api--------")

        job_id = str(uuid.uuid4())
        if spatial_query_only:
            job_id = "query-" + job_id
        else:
            job_id = "subset-" + job_id

        task = _perform_subset.apply_async((watershed_geometry,
                                           watershed_epsg,
                                           subset_parameter_dict),
                                           {"job_id":job_id,
                                             "zip_results":True,
                                             "query_only": spatial_query_only,},
                                           task_id=job_id,
                                           countdown=3,)
                                           # time_limit=nwm_viewer_subsetting_time_limit,  # 30 minutes
                                           # soft_time_limit=nwm_viewer_subsetting_soft_time_limit,  # 20 minutes
                                           # rate_limit=nwm_viewer_subsetting_rate_limit)  # 10 request/min

        response = JsonResponse({"job_id": task.task_id, "status": task.state})
        logger.info("------END: subset_watershed_api--------")
        return response

    except Exception as ex:
        logger.exception(ex.message)
        logger.error("------ERROR: subset_watershed_api--------")
        return HttpResponse(status=500, content=ex.message)


@api_view(['GET'])
@authentication_classes((TokenAuthentication, SessionAuthentication))
def check_subsetting_job_status(request):
    job_id = request.GET.get("job_id", None)
    try:
        if job_id:
            result = _perform_subset.AsyncResult(job_id)
            return JsonResponse({"status": result.state})
        else:
            JsonResponse({"error": "No job_id is provided"})
    except Exception as ex:
        return HttpResponse(status=500, content=ex.message)


@api_view(['GET'])
@authentication_classes((TokenAuthentication, SessionAuthentication))
def download_subsetting_results(request):
    job_id = request.GET.get("job_id", None)
    try:
        if job_id:
            result = _perform_subset.AsyncResult(job_id)
            if result.ready():
                rslt = result.get()
                if job_id.startswith("subset"):
                    bag_save_to_path = rslt[1]
                    zip_file_path = bag_save_to_path
                    response = FileResponse(open(zip_file_path, 'rb'), content_type='application/zip')
                    response['Content-Disposition'] = 'attachment; filename="' + '{0}.zip"'.format(job_id)
                    response['Content-Length'] = os.path.getsize(bag_save_to_path)
                    return response
                elif job_id.startswith("query"):
                    return JsonResponse(rslt)
            else:
                JsonResponse({"error": "Job is not ready for download yet: {0}".format(job_id)})
        else:
            JsonResponse({"error": "No job_id is provided"})
    except Exception as ex:
        return HttpResponse(status=500, content=ex.message)


@api_view(['GET'])
@authentication_classes((TokenAuthentication, SessionAuthentication))
def check_latest_data_api(request):
    try:
        latest_dict = _check_latest_data()
        return JsonResponse(latest_dict)
    except Exception as ex:
        logger.exception("check_latest_data_api: {0}".format(str(ex)))
        return JsonResponse({"status": "error", "msg": str(ex)})
