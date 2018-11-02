import glob
import os
import shutil
from datetime import datetime, timedelta


def rename_nwm_AA_forcing(date_list, nwm_focring_base_dir, out_dir_path):


    wrf_hydro_forcing_path = out_dir_path
    for date_obj in date_list:

        date_str = date_obj.strftime("%Y%m%d")
        nwm_focring_path = os.path.join(nwm_focring_base_dir, "nwm.{date}/forcing_analysis_assim".format(date=date_str))


        wrf_file_template = "{date}{hour}.LDASIN_DOMAIN1"


        wild_path = os.path.join(nwm_focring_path, "nwm.t*z.analysis_assim.forcing.tm00.conus.nc")
        g=glob.glob(wild_path)
        g.sort()

        for nwm_file_path in g:
            nwm_file_name = os.path.basename(nwm_file_path)
            hour_str = nwm_file_name[5:7]
            wrf_file_name = wrf_file_template.format(date=date_str, hour=hour_str)
            wrf_file_path = os.path.join(wrf_hydro_forcing_path, wrf_file_name)
            #os.symlink(nwm_file_path, wrf_file_path)
            shutil.copyfile(nwm_file_path, wrf_file_path)


def rename_nwm_MR_forcing(nwm_forcing_base_dir, run_date, run_cycle, out_dir_path):
    wrf_hydro_forcing_path = out_dir_path

    nwm_forcing_data_dir = os.path.join(nwm_forcing_base_dir, "nwm.{run_date}".format(run_date=run_date), "forcing_medium_range")


    wrf_file_template = "{datetime}.LDASIN_DOMAIN1"

    wild_path = os.path.join(nwm_forcing_data_dir, "nwm.t{run_cycle}z.medium_range.forcing.f*.conus.nc".
                             format(run_cycle=run_cycle))
    g = glob.glob(wild_path)
    g.sort()

    for nwm_file_path in g:
        nwm_file_name = os.path.basename(nwm_file_path)
        forecast_hour_step = int(nwm_file_name[-12:-9])
        run_datetime_str = run_date + run_cycle
        run_datetime_obj = datetime.strptime(run_datetime_str, "%Y%m%d%H")
        forecast_datetime_obj = run_datetime_obj + timedelta(hours=forecast_hour_step)

        wrf_file_datetime_str = forecast_datetime_obj.strftime("%Y%m%d%H")
        wrf_file_name = wrf_file_template.format(datetime=wrf_file_datetime_str)
        wrf_file_path = os.path.join(wrf_hydro_forcing_path, wrf_file_name)
        # os.symlink(nwm_file_path, wrf_file_path)
        shutil.copyfile(nwm_file_path, wrf_file_path)



# start date
date_start = datetime.strptime("20181001", "%Y%m%d")
# end date
date_end = datetime.strptime("20181003", "%Y%m%d")
days = (date_end - date_start).days + 1

date_list = [date_start + timedelta(days=x) for x in range(0, days)]
date_list.sort()


# Source: Where is the NWM style subsetted files
nwm_focring_base_dir = "/home/drew/AA_subsetted/nwm"

# Target: output renamed files (wrfhydro style) to
wrf_hydro_forcing_path = "/home/drew/AA_subsetted/wrfhydro"
# run rename function
rename_nwm_AA_forcing(date_list, nwm_focring_base_dir, wrf_hydro_forcing_path)


#nwm_forcing_base_dir = "/home/drew/croton_NY/New_data/mr/"
#wrf_hydro_forcing_path = "/home/drew/croton_NY/New_data/mr/nwm.20180514/renamed_forcing"
#rename_nwm_MR_forcing(nwm_forcing_base_dir, "20180514", "12", wrf_hydro_forcing_path)


exit(1)