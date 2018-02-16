import json
import time
import logging
import uuid
import os

from django.http import JsonResponse, HttpResponse, FileResponse

from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes

from .utilitiles import _do_spatial_query, _perform_subset, _check_latest_data
from .configs import *

logger = logging.getLogger(__name__)


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
                                           countdown=3,
                                           time_limit=nwm_viewer_subsetting_time_limit,  # 30 minutes
                                           soft_time_limit=nwm_viewer_subsetting_soft_time_limit,  # 20 minutes
                                           rate_limit=nwm_viewer_subsetting_rate_limit)  # 10 request/min

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
