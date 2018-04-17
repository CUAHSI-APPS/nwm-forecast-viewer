import os
import json
import logging
import shutil
import tempfile
import xmltodict

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, FileResponse, HttpResponse

from .timeseries_utilities import _get_netcdf_data
from .subset_utilities import _perform_subset, _find_all_files_in_folder, _zip_folder_contents
from .hs_logic import _add_shp_geojson_to_hs, _get_geojson_from_hs_resource

from tethys_services.backends.hs_restclient_helper import get_oauth_hs

logger = logging.getLogger(__name__)

@login_required()
def get_netcdf_data(request):

    return _get_netcdf_data(request)


@login_required()
def get_hs_watershed_list(request):
    response_obj = {}
    hs_username = ""
    try:
        if not request.session.get("hydroshare_ready", False):
            raise Exception("not logged in via hydroshare")
        if request.is_ajax() and request.method == 'GET':
            resources_list = []
            hs = get_oauth_hs(request)
            if hs is None:
                response_obj['error'] = 'You must be signed in through HydroShare to access this feature. ' \
                                        'Please log out and then sign in again using your HydroShare account.'
            else:
                owner = None
                try:
                    owner = hs.getUserInfo()['username']
                    hs_username = owner
                except Exception:
                    pass

                # loop through all Generic and Feature res current user owns
                valid_res_types = ['GenericResource', 'GeographicFeatureResource']

                for resource in hs.getResourceList(types=valid_res_types, owner=owner):
                #for resource in hs.getResourceList(types=valid_res_types):
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
                        logger.exception(ex)
                        logger.error("Failed res in get_hs_watershed_list: " + str(resource))

                resources_json = json.dumps(resources_list)

                response_obj['success'] = 'Resources obtained successfully.'
                response_obj['resources'] = resources_json
                response_obj['hs_username'] = hs_username
        else:
            raise Exception("not a ajax GET request")

    except Exception as ex:
        logger.exception(ex)
        response_obj = {"error": "Failed to load resources from HydroShare. Did you sign in with your HydroShare account?"}
    finally:
        return JsonResponse(response_obj)


@login_required()
def load_watershed(request):

    if not request.session.get("hydroshare_ready", False):
        raise Exception("not logged in via hydroshare")

    tmp_dir = None
    try:
        if request.is_ajax() and request.method == 'POST':

            res_id = str(request.POST['res_id'])
            filename = str(request.POST['filename'])
            res_title = request.POST.get('res_title')
            add_to_hs = request.POST.get('add_to_hs')
            uploaded_files = request.FILES.getlist('files')
            tmp_dir = tempfile.mkdtemp()

            #save local files
            shp_geojson_local_path = None
            f_path_list = []
            for f in uploaded_files:
                f_name = f.name
                f_path = os.path.join(tmp_dir, f_name)
                if f_path.lower().endswith(".shp"):
                    shp_geojson_local_path = f_path
                elif f_path.lower().endswith(".geojson"):
                    shp_geojson_local_path = f_path
                with open(f_path, 'wb') as f_local:
                    f_local.write(f.read())
                    f_path_list.append(f_path)

            if add_to_hs == "true" and len(uploaded_files) > 0 and shp_geojson_local_path:  # upload to hydroshare
                logger.debug("pushing to hs")
                logger.debug(shp_geojson_local_path)
                res_id = _add_shp_geojson_to_hs(request, shp_geojson_local_path, res_title)
                logger.debug("done pushing to hs")

            response_obj = _get_geojson_from_hs_resource(request, res_id, filename, shp_geojson_local_path)

            shutil.rmtree(tmp_dir)

            return JsonResponse(response_obj)

    except Exception as ex:
        logger.exception(ex)
        return JsonResponse({'error': "Failed to load watershed"})
    finally:
        if tmp_dir is not None and os.path.exists(tmp_dir):
            shutil.rmtree(tmp_dir)


@login_required()
def subset_watershed(request):

    job_folder_path = None
    binary_file_name = None
    binary_file_path = None
    upload_to_hydroshare = False

    try:
        if not request.session.get("hydroshare_ready", False):
            raise Exception("not logged in via hydroshare")
        if request.method == 'POST':

            request_dict = json.loads(request.body)
            if "hydroshare" in request_dict:
                upload_to_hydroshare = True

            job_id, job_folder_path = _perform_subset(request_dict['watershed_geometry'],
                                                       int(request_dict['watershed_epsg']),
                                                       request_dict['subset_parameter'])

            nc_file_list = _find_all_files_in_folder(job_folder_path, ".nc")
            nc_file_list_count = len(nc_file_list)
            hs_res_type = None
            if nc_file_list_count == 1:
                # only one nc file --> netcdf resource type
                hs_res_type = "NetcdfResource"
                binary_file_path = nc_file_list[0]
                binary_file_name = os.path.basename(binary_file_path)
                pass
            elif nc_file_list_count == 0:
                # 0 --> error
                raise Exception("No netcdf file")
            else:
                # more than one nc file --> composite resource type
                hs_res_type = "CompositeResource"
                # zip it up first
                zip_file_path = job_folder_path + '.zip'
                _zip_folder_contents(zip_file_path, job_folder_path)
                binary_file_path = zip_file_path
                binary_file_name = job_id + ".zip"
                pass

            # upload to hydroshare
            if upload_to_hydroshare:
                hs = get_oauth_hs(request)
                hydroshare_dict = request_dict["hydroshare"]
                if hs_res_type == "CompositeResource":
                    resource_id = hs.createResource("CompositeResource",
                                                    hydroshare_dict["title"],
                                                    keywords=hydroshare_dict["keywords"].split(','),
                                                    abstract=hydroshare_dict["abstract"])

                    resource_id = hs.addResourceFile(resource_id, binary_file_path)

                    options = {
                                "zip_with_rel_path": os.path.basename(binary_file_path),
                                "remove_original_zip": True
                              }

                    unzipping_resp = hs.resource(resource_id).functions.unzip(options)

                elif hs_res_type == "NetcdfResource":
                    resource_id = hs.createResource("NetcdfResource",
                                                    hydroshare_dict["title"],
                                                    resource_file=binary_file_path,
                                                    keywords=hydroshare_dict["keywords"].split(','),
                                                    abstract=hydroshare_dict["abstract"])
                else:
                    raise Exception("wrong resource type")

                return JsonResponse({"status": "success", "res_id": resource_id})

            else:  # return file binary stream

                response = FileResponse(open(binary_file_path, 'rb'), content_type='application/zip' if binary_file_name
                                        .endswith(".zip") else "application/x-cdf")
                response['Content-Disposition'] = 'attachment; filename="' + '{0}"'.format(binary_file_name)
                response['Content-Length'] = os.path.getsize(binary_file_path)
                return response
        else:
            if upload_to_hydroshare:
                return JsonResponse({"status": "error"})
            else:
                return HttpResponse(status=500, content="Not a POST request")
    except Exception as ex:
        logger.exception(type(ex))
        logger.exception(ex)
        if upload_to_hydroshare:
            return JsonResponse({"status": "error", "msg": ex.message})
        else:
            return HttpResponse(status=500, content=ex.message)
    finally:
        if job_folder_path is not None:
            if os.path.exists(job_folder_path + ".zip"):
                os.remove(job_folder_path + ".zip")
            if os.path.exists(job_folder_path):
                shutil.rmtree(job_folder_path)


@login_required()
def upload_to_hydroshare(request):
    temp_dir = None
    try:
        if not request.session.get("hydroshare_ready", False):
            raise Exception("not logged in via hydroshare")
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
