import logging
import os
import tempfile
import shutil
import geojson
import fiona
import shapely
from shapely import wkt
from osgeo import ogr

from .subset_utilities import _zip_folder_contents, reproject_wkt_gdal
from tethys_services.backends.hs_restclient_helper import get_oauth_hs

logger = logging.getLogger(__name__)


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
                content = next(hs.getResourceFile(pid=res_id, filename=filename))
                if type(content) is bytes:
                    geojson_str = content.decode('utf-8')
                else:
                    geojson_str = str(next(hs.getResourceFile(pid=res_id, filename=filename)))
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
                proj_str_raw = str(next(hs.getResourceFile(pid=res_id, filename=filename.replace('.shp', '.prj'))))
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
