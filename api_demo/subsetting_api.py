import os
import json
import zipfile

import requests
from osgeo import osr
from osgeo import ogr
import shapely
import shapely.wkt
import shapely.geometry
import fiona
import netCDF4
import matplotlib.pyplot as plt
import numpy as np

from hs_restclient import HydroShare, HydroShareAuthBasic


def extract_polygon_geojson_from_shapefile(shp_path):
    '''
    read a shp file, extract its first polygon, reproject it into WGS84/EPSG:4326, convert it to GeoJSON string
    :param shp_path: full path to *.shp file
    :return: GeoJSON string
    '''

    shp_obj = fiona.open(shp_path)
    first_feature_obj = next(shp_obj)
    shape_obj = shapely.geometry.shape(first_feature_obj["geometry"])

    # convert 3D geom to 2D
    if shape_obj.has_z:
        wkt2D = shape_obj.wkt
        shape_obj = shapely.wkt.loads(wkt2D)

    if shape_obj.geom_type.lower() == "multipolygon":
        polygon_exterior_linearring = shape_obj[0].exterior
    elif shape_obj.geom_type.lower() == "polygon":
        polygon_exterior_linearring = shape_obj.exterior
    else:
        raise Exception("Input Geometry is not Polygon")

    polygon_exterior_linearring_shape_obj = shapely.geometry.Polygon(polygon_exterior_linearring)

    prj_str = None
    prj_path = shp_path.replace(".shp", ".prj")
    with open(prj_path, 'r') as content_file:
        prj_str_raw = content_file.read()
        prj_str = prj_str_raw.replace('\n', '')

    # use gdal for coordinate re-projection
    wkt_4326 = _reproject_wkt_gdal(polygon_exterior_linearring_shape_obj.wkt,
                                   prj_str,
                                   4326)
    geojson_str_4326 = ogr.CreateGeometryFromWkt(wkt_4326).ExportToJson()

    return geojson_str_4326


def _reproject_wkt_gdal(in_wkt, in_prj_str, out_epsg):

    """
    Re-project the wkt string from the projection defined by a ESRI projection string to projection defined by EPSG code
    :param in_wkt:
    :param in_prj_str:
    :param out_epsg:
    :return:
    """
    if 'GDAL_DATA' not in os.environ:
        raise Exception("Environment variable 'GDAL_DATA' not found!")

    source = osr.SpatialReference()
    source.ImportFromESRI([in_prj_str])

    target = osr.SpatialReference()
    target.ImportFromEPSG(out_epsg)

    transform = osr.CoordinateTransformation(source, target)

    geom_gdal = ogr.CreateGeometryFromWkt(in_wkt)
    geom_gdal.Transform(transform)

    return geom_gdal.ExportToWkt()


def list_comids(netcdf_path, length_only=False):
    '''
    List all comids values or total number in a NWM netcdf
    :param netcdf_path: full path to NWM netcdf file
    :param length_only: if True, return total number of contained comids; Default: False
    :return: all contained comid values in a list, or total number of comids if length_only=True
    '''

    with netCDF4.Dataset(netcdf_path, mode='r', format="NETCDF4_CLASSIC") as in_nc:
        if length_only:
            return len(in_nc.variables["feature_id"])
        else:
            return list(in_nc.variables["feature_id"][:])


def list_hydrologic_variables(netcdf_path):
    '''
    List all name of all cotained hydrologic variables
    :param netcdf_path: netcdf path
    :return: list of variable names
    '''
    hydrologic_var_list = []
    with netCDF4.Dataset(netcdf_path, mode='r', format="NETCDF4_CLASSIC") as in_nc:
        for name, var_obj in in_nc.variables.iteritems():
            if len(var_obj.dimensions) > 1 and var_obj.dimensions[0] == "time":
                hydrologic_var_list.append(name)
    return hydrologic_var_list


def get_variable_values(netcdf_path, var_name, comid, datetime_format=None, paired=False):
    '''
    Retrieve timeseries for a variable of a given comid
    :param netcdf_path: netcdf file path
    :param var_name: variable name
    :param comid: set to comid value if netcdf is Stream or Reservoir; Set to None or "grid" if netcdf is Forcing or Land
    :param datetime_format: datetime string format in output; If set to None, return datetime object
                            IF set to "%Y%m%d-%H:%M:%S", return YYYYMMDD-HH:MM:SS;  Default: None
    :param paired: If True, return one list: [[time1, value1], [time2, value2]...]
                   If False, return two lists: [time1, time2], [value1, value2...]
                   Default: False
    :return: see paired
    '''
    t_series = []
    time_list = []
    value_list = []
    with netCDF4.Dataset(netcdf_path, mode='r', format="NETCDF4_CLASSIC") as in_nc:

        var_time = in_nc.variables["time"]
        if datetime_format is None:
            time_list = [netCDF4.num2date(t, var_time.units) for t in var_time[:]]
        else:
            time_list = [netCDF4.num2date(t, var_time.units).strftime(datetime_format) for t in var_time[:]]

        if comid is None or str(comid).lower() == "grid":
            value_list = list(in_nc.variables[var_name][:])
        else:
            # find index for input comid:
            comid_index = -1
            for idx in range(len(in_nc.variables["feature_id"][:])):
                if in_nc.variables["feature_id"][idx] == int(comid):
                    comid_index = idx
                    break
            value_list = list(in_nc.variables[var_name][:, comid_index])

    if paired:
        for index in range(len(time_list)):
            t_series.append([time_list[index], value_list[index]])
        return t_series
    else:
        return time_list, value_list


# Entry Point
if __name__ == "__main__":

    ########################## Subsetting API ################################
    workspace_path = "/tmp"

    # full path to a local shapefile (*.shp)
    shp_path = None
    # or use a hydroshare geographic feature resource
    use_hydroshare = True
    ########################## input HydroShare account info if above 'use_hydroshare' is True #################
    hs_username = "USERNAME"  # Your hydroshare username
    hs_password = "PASSWORD"  # Your hydroshare password
    # hydroshare geographic feature resource id
    # TwoMileCreek watershed at Tuscaloosa, Alabama
    # This is a public resource so anyone can access it.
    res_id = "33a54c751e4f465397f3bbadfb220053"

    if use_hydroshare:
        auth = HydroShareAuthBasic(username=hs_username, password=hs_password)
        hs = HydroShare(auth=auth)

        hs.getResource(res_id, destination=workspace_path, unzip=True)
        content_folder_path = os.path.join(workspace_path, res_id)
        # find *.shp file
        for root, dirs, files in os.walk(content_folder_path):
            for f in files:
                if f.endswith(".shp"):
                    shp_path = os.path.join(root, f)
                    break

    if shp_path is None:
        print "Can not find any *.shp file"
        exit()

    # extract the first simple Polygon from shapefile; re-project it into WGS84
    # and convert it to GeoJSON string
    geojson_str_4326 = extract_polygon_geojson_from_shapefile(shp_path)

    # prepare the data sent to api endpoint
    data = {
        'subset_parameter': {
            'config': "analysis_assim",  # analysis_assim, short_range, medium_range, long_range
            'startDate': "2017-06-10",  # 2017-06-01
            'endDate': "2017-06-11",  # 2017-06-02 (only for analysis_assim)
            'geom': "land",  # channel_rt, reservoir, land, forcing
            'time': "01",  # 00, 01 ...23 (only for short_range and medium_range)
            'lag_00z': "on",  # "on" or ""  (only for long_range)
            'lag_06z': "",
            'lag_12z': "",
            'lag_18z': "",
            'merge': True  # True or False
        },
        'watershed_epsg': 4326,  # keep this unchanged as latest GeoJSON standard requires coordinates in WGS84/EPSG:4326 projection
                                 # see: https://tools.ietf.org/html/rfc7946#section-4
        'watershed_geometry': geojson_str_4326  # the polygon geojson string extracted from shapefile
    }

    # Note: this URL api endpoint must end with a slash '/'
    resp = requests.post('https://appsdev.hydroshare.org/apps/nwm-forecasts/subset-watershed-api/',
                            data=json.dumps(data),
                            verify=False)

    # save api response as a local zip file
    netcdf_file_list = []
    if resp.status_code == 200:
        zip_filename = resp.headers['Content-Disposition'].split(";")[1].split("=")[1].replace('"', '')
        job_id = zip_filename[:-4]
        job_id_folder_path = os.path.join(workspace_path, job_id)
        os.mkdir(job_id_folder_path)
        zip_path = os.path.join(job_id_folder_path, zip_filename)
        with open(zip_path, 'wb+') as f:
            for chunk in resp.content:
                f.write(chunk)

        # unzip it
        zip_ref = zipfile.ZipFile(zip_path, 'r')
        zip_ref.extractall(job_id_folder_path)
        zip_ref.close()

        # loop through it and find all *.nc files
        print "Subsetted NWM netcdf files are stored at:"
        for root, dirs, files in os.walk(job_id_folder_path):
            for f in files:
                if f.endswith(".nc"):
                    netcdf_file_list.append(os.path.join(root, f))
        print netcdf_file_list
    else:
        print "Failed to subset watershed"
        exit()


    ########################## Plotting ################################
    # pick the first *.nc file in 'netcdf_file_list' for visualization demo
    netcdf_path = netcdf_file_list[0]

    # list all variables in netcdf
    print list_hydrologic_variables(netcdf_path)

    # get timeseries for var "SOILSAT_TOP"
    date_list, value_list = get_variable_values(netcdf_path, "SOILSAT_TOP", None)

    for i in range(len(date_list)):
        timestamp = date_list[i]
        # Plot each timestamp
        array_2d = value_list[i]
        # The origin point of the array retrieved from netcdf file is in upper-left corner (North pointing downward)
        # We need to make North face upward before plotting it in matplotlib.pyplot
        # Flip array in the up/down direction
        # see: https://docs.scipy.org/doc/numpy-dev/reference/generated/numpy.flipud.html#numpy.flipud
        # [[1, 2],   -->  [[3, 4],
        #  [3, 4]]         [1, 2]]
        array_2d_flipped = np.flipud(array_2d)
        title = timestamp.strftime("%Y-%m-%d, %H:%M:%S") + " ({0}/{1})".format(i + 1, len(date_list))
        plt.title(title, fontsize=15)
        plt.imshow(array_2d_flipped, interpolation="none")
        plt.colorbar()
        plt.show()
