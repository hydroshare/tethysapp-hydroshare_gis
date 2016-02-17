from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist

from oauthlib.oauth2 import TokenExpiredError
from utilities import *

# import shapefile
import os
import shutil
from json import dumps

hs_tempdir = '/tmp/hs_gis_files/'


@login_required()
def home(request):
    """
    Controller for the app home page.

    :param request: the request object sent by the browser
    """

    context = {}

    return render(request, 'hydroshare_gis/home.html', context)


def load_file(request):
    """
    Controller for the "Load file from computer" button.

    :param request: the request object sent by the browser
    :returns JsonResponse: a JSON formatted response containing success value and GeoJSON object if successful
    """
    global hs_tempdir
    # shp_file_object = None
    # dbf_file_object = None
    # shx_file_obejct = None
    # prj_file_content = None
    res_id = None
    res_type = None
    res_path_or_obj = None
    is_zip = None

    if not os.path.exists(hs_tempdir):
        os.mkdir(hs_tempdir)

    if request.is_ajax() and request.method == 'POST':

        # Get/check files from AJAX request
        res_path_or_obj = request.FILES.getlist('files')

        if len(res_path_or_obj) == 1:
            is_zip = True
        else:
            for shp_file in res_path_or_obj:
                file_name = shp_file.name
                if file_name.endswith('.shp'):
                    res_id = str(file_name[:-4].__hash__())
                    res_type = 'GeographicFeatureResource'
                elif file_name.endswith('.tif'):
                    res_id = str(file_name[:-4].__hash__())
                    res_type = 'RasterResource'

        # for shp_file in res_path_or_obj:
        #     file_name = shp_file.name
        #     if file_name.endswith('.shp'):
        #         shp_file_object = shp_file
        #         filename = file_name
        #     elif file_name.endswith('.dbf'):
        #         dbf_file_object = shp_file
        #     elif file_name.endswith('.shx'):
        #         shx_file_obejct = shp_file
        #     elif file_name.endswith('.prj'):
        #         prj_file_content = shp_file.read()

    elif request.is_ajax() and request.method == 'GET':
        try:
            res_id = request.GET['res_id']
            # hs = get_oauth_hs(request)
            hs = HydroShare()
            res_type = hs.getSystemMetadata(res_id)['resource_type']
            hs.getResource(res_id, destination=hs_tempdir, unzip=True)
            res_contents_dir = os.path.join(hs_tempdir, res_id, res_id, 'data', 'contents')
            is_zip = False

            if os.path.exists(res_contents_dir):
                for file_name in os.listdir(res_contents_dir):
                    if file_name.endswith('.shp'):
                        res_path_or_obj = os.path.join(res_contents_dir, file_name[:-4])
                    elif file_name.endswith('.tif'):
                        res_path_or_obj = os.path.join(res_contents_dir, file_name)

        except ObjectDoesNotExist as e:
            print str(e)
            return get_json_response('error', 'Login timed out! Please re-sign in with your HydroShare account.')
        except TokenExpiredError as e:
            print str(e)
            return get_json_response('error', 'Login timed out! Please re-sign in with your HydroShare account.')
        except Exception, err:
            if "401 Unauthorized" in str(err):
                return get_json_response('error', 'Username or password invalid.')

    else:
        return get_json_response('error', 'Invalid request made.')

    layer_name, layer_id = store_file_on_geoserver(res_id, res_type, res_path_or_obj, is_zip)

    # '''
    # Credit: The following code was adapted from https://gist.github.com/frankrowe/6071443
    # '''
    # # Read the shapefile-like object
    # shp_reader = shapefile.Reader(shp=shp_file_object, dbf=dbf_file_object, shx=shx_file_obejct)
    # fields = shp_reader.fields[1:]
    # field_names = [field[0] for field in fields]
    # shp_buffer = []
    # for sr in shp_reader.shapeRecords():
    #     atr = dict(zip(field_names, sr.record))
    #     geom = sr.shape.__geo_interface__
    #     shp_buffer.append(dict(type="Feature", geometry=geom, properties=atr))
    #
    # shp_file_object.close()
    # dbf_file_object.close()
    # shx_file_obejct.close()

    # # Write the GeoJSON object
    # geojson = dumps({"type": "FeatureCollection", "features": shp_buffer}, indent=2) + "\n"
    # '''
    # End credit
    # '''

    if res_id:
        if os.path.exists(os.path.join(hs_tempdir, res_id)):
            shutil.rmtree(os.path.join(hs_tempdir, res_id))

    # return JsonResponse({
    #     'success': 'Files uploaded successfully.',
    #     'geojson': geojson,
    #     'projection': prj_file_content,
    #     'filename': filename
    # })

    return JsonResponse({
        'success': 'Files uploaded successfully.',
        'geoserver_url': geoserver_url,
        'layer_name': layer_name,
        'layer_id': layer_id
    })


def get_hs_res_list(request):
    if request.is_ajax() and request.method == 'GET':
        valid_res_list = []

        # hs = get_oauth_hs(request)
        hs = HydroShare()
        for resource in hs.getResourceList():
            if resource['resource_type'] == 'GeographicFeatureResource':
                    # or resource['resource_type'] == 'RasterResource':

                valid_res_list.append({
                    'title': resource['resource_title'],
                    'type': resource['resource_type'],
                    'id': resource['resource_id']
                })

        valid_res_json = dumps(valid_res_list)

        return JsonResponse({
            'success': 'Resources obtained successfully.',
            'resources': valid_res_json
        })
