import uuid
import datetime
import logging
import os
import re
import shutil
import zipfile

from django_celery_results.models import TaskResult
from django.db.models import Q

from celery import shared_task
from celery.task import periodic_task
from celery.schedules import crontab

from subset_nwm_netcdf.subset import start_subset_nwm_netcdf_job
from subset_nwm_netcdf.merge import start_merge_nwm_netcdf_job
from subset_nwm_netcdf.query import query_comids_and_grid_indices

from .configs import *

logger = logging.getLogger(__name__)


def _do_spatial_query(geom_str, in_epsg, job_id=None):

    query_type = "geojson"
    shp_path = None
    huc_id = None
    query_result_dict = query_comids_and_grid_indices(job_id=job_id,
                                                      db_file_path=db_file_path,
                                                      query_type=query_type,
                                                      shp_path=shp_path,
                                                      geom_str=geom_str,
                                                      in_epsg=in_epsg,
                                                      huc_id=huc_id)
    return query_result_dict


@shared_task
def _perform_subset(geom_str, in_epsg, subset_parameter_dict, job_id=None, zip_results=False, query_only=False):

    if not job_id:
        job_id = str(uuid.uuid4())

    all_start_dt = datetime.datetime.now()
    logger.info("-------------Process Started-------------------")
    logger.info(all_start_dt)

    query_result_dict = _do_spatial_query(geom_str, in_epsg, job_id=job_id)
    if query_only:
        logger.info("-------------Spatial Query Only-------------------")
        return query_result_dict

    if query_result_dict is None:
        raise Exception("Failed to retrieve spatial query result")

    # Path of output folder
    # output_folder_path = "/tmp"
    output_folder_path = app_workspace.path
    logger.info("**************app_workspace*********************")
    logger.info(output_folder_path)

    # shrink dimension size to cover subsetting domain only
    resize_dimension_grid = True
    resize_dimension_feature = True
    merge_netcdfs = True
    # remove intermediate files
    cleanup = True

    # list of simulation dates
    simulation_date_list = []
    startDate_str = subset_parameter_dict.get("startDate", "")
    endDate_str = subset_parameter_dict.get("endDate", "")

    if subset_parameter_dict["config"] == "analysis_assim":
        if endDate_str.lower() == "latest":
            latest_data_info_dict = _check_latest_data()
            if local_vm_test:
                endDate_obj = datetime.datetime.strptime(local_vm_test_data_date, "%Y%m%d")
            else:
                #endDate_obj = datetime.datetime.utcnow()
                config_geometry_string = subset_parameter_dict["config"] + "." + subset_parameter_dict["geom"]
                analysis_assim_geometry = latest_data_info_dict.get(config_geometry_string, None)

                if analysis_assim_geometry:
                    endDate_str = analysis_assim_geometry["date"]
                    endDate_obj = datetime.datetime.strptime(endDate_str, "%Y%m%d")
                else:
                    raise Exception("Failed to check latest analysis_assim")

            if startDate_str.isdigit():  # num of days before today
                days_before = datetime.timedelta(days=-1 * abs(int(startDate_str)))
                startDate_obj = endDate_obj + days_before
            elif startDate_str == "" or startDate_str == "latest":
                startDate_obj = endDate_obj
            else:
                startDate_obj = datetime.datetime.strptime(startDate_str, "%Y-%m-%d")

        elif endDate_str: # not ""
            endDate_obj = datetime.datetime.strptime(endDate_str, "%Y-%m-%d")

            if startDate_str:
                startDate_obj = datetime.datetime.strptime(startDate_str, "%Y-%m-%d")
            else:
                raise Exception("startDate is not set")
        else:
            raise Exception("endDate is not set")

        if endDate_obj < startDate_obj:
            raise Exception("endDate is earlier than startDate.")

        dateDelta_obj = endDate_obj - startDate_obj
        dateRange_obj_list = [startDate_obj + datetime.timedelta(days=x) for x in
                              range(0, dateDelta_obj.days + 1)]
        simulation_date_list = [x.strftime("%Y%m%d") for x in dateRange_obj_list]

    else:  # non-"analysis_assim"
        if not startDate_str:
            raise Exception("startDate is not set")
        if startDate_str.lower() == "latest":
            latest_data_info_dict = _check_latest_data()

            if subset_parameter_dict["config"] != "long_range":
                config_geometry_string = subset_parameter_dict["config"] + "." + subset_parameter_dict["geom"]

            else:
                config_geometry_string = subset_parameter_dict["config"] + "." + subset_parameter_dict["geom"] + ".mem" + subset_parameter_dict["mem"]

            subset_parameter_dict["time"] = latest_data_info_dict[config_geometry_string]["time"]

            simulation_date_list = [latest_data_info_dict[config_geometry_string]["date"]]
        else:
            simulation_date_list = [startDate_str.replace("-", "")]


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
    # elif subset_parameter_dict['config'] == "long_range":
    #     time_stamp_list = []
    #     if subset_parameter_dict['lag_00z'] == "on":
    #         time_stamp_list.append(0)
    #     if subset_parameter_dict['lag_06z'] == "on":
    #         time_stamp_list.append(6)
    #     if subset_parameter_dict['lag_12z'] == "on":
    #         time_stamp_list.append(12)
    #     if subset_parameter_dict['lag_18z'] == "on":
    #         time_stamp_list.append(18)
    else:
        time_stamp_list = [int(subset_parameter_dict['time'])]

    grid_land_dict = query_result_dict["grid_land"]
    grid_terrain_dict = query_result_dict["grid_terrain"]
    stream_comid_list = query_result_dict["stream"]["comids"]
    reservoir_comid_list = query_result_dict["reservoir"]["comids"]

    if "long_range" in model_configuration_list:
        model_configuration_list.remove("long_range")
        # for i in range(1, 5):
        #     model_configuration_list.append("long_range_mem{0}".format(str(i)))
        mem_parameter = subset_parameter_dict.get('mem', None)
        if mem_parameter is None:
            # request comes from API, not UI
            mem_index = 0
            for lag_name in ["lag_00z", "lag_06z", "lag_12z", "lag_18z"]:
                mem_index += 1
                lag_value = subset_parameter_dict.get(lag_name, None)
                if lag_value.lower() == "on":
                    model_configuration_list.append("long_range_mem{0}".format(str(mem_index)))
        elif isinstance(mem_parameter, basestring) and (1 <= int(mem_parameter) <= 4):
            # request comes from API and is a list
            for i in mem_parameter:
                model_configuration_list.append("long_range_mem{0}".format(str(i)))
        else:
            raise Exception("invalid 'mem' parameter for Long Range")


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


@periodic_task(run_every=crontab(minute=nwm_viewer_subsetting_clean_up_minute, hour=nwm_viewer_subsetting_clean_up_hour), ignore_result=False)
def clean_up_subsetting_results():
    try:
        utc_current = pytz.utc.localize(datetime.datetime.utcnow())
        d_time = datetime.timedelta(minutes=-1*nwm_viewer_subsetting_result_life_minute)
        utc_expired = utc_current + d_time

        for task_i in TaskResult.objects.filter(Q(date_done__lt=utc_expired,
                                                  task_id__startswith='subset',
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
        return "Clean up subset results done"

    except Exception as ex:
        logger.exception(ex)
        return str(ex)


def _check_latest_data():

    nomads_root = netcdf_folder_path

    # get latest date:
    r = re.compile(r"nwm\.20\d\d\d\d\d\d")
    dir_name_list = filter(lambda x: os.path.isdir(os.path.join(nomads_root, x)) and r.match(x),
                           os.listdir(nomads_root))
    dir_name_list.sort(key=lambda x: int(x.split('.')[1]), reverse=True)
    config_list = ["analysis_assim", "short_range", "medium_range", "long_range"]
    geom_list = ["forcing", "channel_rt", "reservoir", "land", "terrain_rt"]

    rslt_list = {}
    rslt_list["checked_at_utc"] = datetime.datetime.utcnow().strftime("%Y%m%d-%H:%M:%S")
    for date_dir in dir_name_list:
        date_path = os.path.join(nomads_root, date_dir)
        date_string = date_dir.split(".")[1]
        # all file names in one list
        filename_list = []
        for dirpath, dirnames, filenames in os.walk(date_path):
            filename_list = filename_list + filenames
        for config in config_list:
            for geom in geom_list:
                if config == "long_range" and (geom == "forcing" or geom == "terrain_rt"):
                    continue
                if config == "long_range":
                    for mem_i in range(1, 5):
                        _build_latest_dict_info(rslt_list, filename_list, date_string, config, geom, mem_i)
                else:
                    _build_latest_dict_info(rslt_list, filename_list, date_string, config, geom, None)
        if len(rslt_list) == 28:  # 27 data items + 1 checked_at_utc item
            break

    # logger.debug("latest data dict length: {0}".format(len(rslt_list)))
    # logger.debug("latest data dict: {0}".format(rslt_list))
    return rslt_list


def _build_latest_dict_info(rslt_list, filename_list, date_string, config, geom, mem_i=None):
    #  called by _check_latest_data()
    if mem_i:
        key_name = config + "." + geom + ".mem" + str(mem_i)
    else:
        key_name = config + "." + geom

    if key_name not in rslt_list:
        if mem_i:
            r = re.compile("nwm.t\\d\\dz.{0}.{1}_{2}.*.conus.nc".format(config, geom, mem_i))
        else:
            r = re.compile("nwm.t\\d\\dz.{0}.{1}.*.conus.nc".format(config, geom))
        newlist = filter(r.match, filename_list)
        if len(newlist) > 0:
            newlist.sort(key=lambda x: int(x.split('.')[1][1:3]), reverse=True)
            max_item = newlist[0]
            rslt_list[key_name] = {"date": date_string, "time": max_item.split('.')[1][1:3]}


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


def _get_current_utc_date():

    if local_vm_test:
        return "2017-04-19", "2017-04-19", "2017-04-19", "2017-04-19"

    date_string_today = datetime.datetime.utcnow().strftime("%Y-%m-%d")
    date_string_oldest = (datetime.datetime.utcnow() + datetime.timedelta(days=-1*nomads_data_days)).strftime("%Y-%m-%d")
    date_string_minus_2 = (datetime.datetime.utcnow() + datetime.timedelta(days=-2)).strftime("%Y-%m-%d")
    date_string_minus_3 = (datetime.datetime.utcnow() + datetime.timedelta(days=-3)).strftime("%Y-%m-%d")

    return date_string_today, date_string_oldest, date_string_minus_2, date_string_minus_3
