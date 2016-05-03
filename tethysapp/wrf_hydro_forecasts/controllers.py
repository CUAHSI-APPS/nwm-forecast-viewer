from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from tethys_sdk.gizmos import MapView, MVView

import os
import netCDF4 as nc
import json

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

    context = {}

    return render(request, 'wrf_hydro_forecasts/home.html', context)


def start_file_download(request):
    global temp_dir, prediction_data, rp_data, total_prediction_comids, total_rp_comids, sorted_prediction_comids, \
        sorted_rp_comids, time
    if request.method == 'GET':
        get_data = request.GET

        try:
            app_dir = os.path.dirname(__file__)
            nc_files = os.listdir(os.path.join(app_dir, 'data'))
            print nc_files

            local_file_path = os.path.join(app_dir, 'data', nc_files[0])
            prediction_data = nc.Dataset(local_file_path, mode="r")

            qout_dimensions = prediction_data.variables['station_id'].dimensions

            if qout_dimensions[0] == 'station':
                sorted_prediction_comids = sorted(enumerate(prediction_data.variables['station_id'][:]),
                                                  key=lambda comid: comid[1])
                total_prediction_comids = len(sorted_prediction_comids)
                print "total_prediction_comids: %s" % total_prediction_comids
            else:
                return JsonResponse({'error': "Invalid netCDF file"})
            variables = prediction_data.variables.keys()
            if 'time' in variables:
                print '*****************'
                print prediction_data.variables['time'][:]
                time = [int(nc.num2date(0, prediction_data.variables['time']
                                         .units).strftime('%s'))]
                print time
            else:
                return JsonResponse({'error': "Invalid netCDF file"})

            rp_data = nc.Dataset(local_file_path, mode="r")
            sorted_rp_comids = sorted(enumerate(rp_data.variables['station_id'][:]), key=lambda comid: comid[1])
            total_rp_comids = len(sorted_rp_comids)
            return JsonResponse({'success': "The file is ready to go."})

        except Exception, err:
            return JsonResponse({'error': err})
    else:
        return JsonResponse({'error': "Bad request. Must be a GET request."})


def get_netcdf_data(request):
    global temp_dir, prediction_data, rp_data, total_prediction_comids, total_rp_comids, sorted_prediction_comids, \
        sorted_rp_comids, time
    if request.method == 'GET':
        print '************************'
        print request.GET
        get_data = request.GET
        ts_pairs_data = {}  # For time series pairs data
        rp_cls_data = {}  # For return period classification data
        rp_bmk_data = {}  # For return period benchmark data
        try:
            comids = str(get_data['comids'])
            print "comids: %s" % comids
            comids = comids.split(',')
            for comid_iter in comids:
                print "comid_iter: %s" % comid_iter
                comid = int(comid_iter)
                prediction_file_index = match_comid_algorithm(comid, total_prediction_comids, sorted_prediction_comids)
                print "prediction_file_index: %s" % prediction_file_index
                if prediction_file_index == -1:
                    if len(comids) == 1:
                        return JsonResponse({'error': "Data for this reach could not be found."})
                    else:
                        q_out = [-9999]
                else:
                    q_out = []
                    app_dir = os.path.dirname(__file__)
                    nc_files = os.listdir(os.path.join(app_dir, 'data'))
                    for ncf in nc_files:
                        local_file_path = os.path.join(app_dir, 'data', ncf)
                        prediction_dataTemp = nc.Dataset(local_file_path, mode="r")
                        q_outT = prediction_dataTemp.variables['streamflow'][prediction_file_index].tolist()
                        print q_outT
                        q_out.append(round(q_outT, 6))
                    print '*******************'
                    print q_out


                rp_file_index = match_comid_algorithm(comid, total_rp_comids, sorted_rp_comids)
                print '999999999999999999999999999999999999'
                print rp_file_index
                rp_benchmarks = []
                if rp_file_index != -1:
                    rp_benchmarks.append(rp_data.variables['station_id'][rp_file_index])

                else:
                    rp_benchmarks.append(-9999)
                    rp_benchmarks.append(-9999)
                    rp_benchmarks.append(-9999)
                rp_classification = []

                for q in q_out:
                    if q == -9999:
                        rp_classification.append(-9999)
                    elif q < rp_benchmarks[0]:
                        rp_classification.append(0)
                    # elif q < rp_benchmarks[1]:
                    #     rp_classification.append(2)
                    # elif q < rp_benchmarks[2]:
                    #     rp_classification.append(10)
                    else:
                        rp_classification.append(20)
                ts_pairs_data[str(comid)] = [time, q_out]
                rp_cls_data[str(comid)] = rp_classification
                # rp_bmk_data[str(comid)] = rp_benchmarks
            return JsonResponse({
                "success": "Data analysis complete!",
                "ts_pairs_data": json.dumps(ts_pairs_data),
                "rp_cls_data": json.dumps(rp_cls_data),
                # "rp_bmk_data": json.dumps(rp_bmk_data)
            })
        except Exception as e:
            print str(e)
            return JsonResponse({'error': e.message})
    else:
        return JsonResponse({'error': "Bad request. Must be a GET request."})


def match_comid_algorithm(comid, count_comids, sorted_comids):
    index = None
    divider = 2
    guess = count_comids / divider
    while (count_comids / divider > 10) and (comid != sorted_comids[guess][1]):
        print "GUESS: %s" % guess
        divider *= 2
        if comid > sorted_comids[guess][1]:
            guess += count_comids / divider
        else:
            guess -= count_comids / divider
    guess = int(guess)
    print "FINAL GUESS: %s" % guess
    iteration = 0
    if comid == sorted_comids[guess][1]:
        print "GUESS WAS CORRECT"
        index = sorted_comids[guess][0]
        return index
    elif comid > sorted_comids[guess][1]:
        print "GUESS WAS LOW"
        while (sorted_comids[guess][1] != comid) and (iteration < 100):
            print "COMID of GUESSED INDEX: %s" % sorted_comids[guess][1]
            guess += 1
            iteration += 1
    else:
        print "GUESS WAS HIGH"
        while (sorted_comids[guess][1] != comid) and (iteration < 100):
            guess -= 1
            iteration += 1
    print "CORRECT GUESS: %s" % guess
    if (index is None) and (iteration < 100):
        index = sorted_comids[guess][0]
        print "CORRECT INDEX: %s" % index
        return index
    else:
        return -1