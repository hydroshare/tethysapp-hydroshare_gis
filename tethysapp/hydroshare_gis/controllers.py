from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist

from oauthlib.oauth2 import TokenExpiredError
from hs_restclient import HydroShare, HydroShareAuthOAuth2

import shapefile
import os
import shutil
from json import dumps

hs_hostname = 'www.hydroshare.org'
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
    shp_file_object = None
    dbf_file_object = None
    shx_file_obejct = None
    prj_file_content = None
    filename = 'shapefile'
    res_id = None

    if request.is_ajax() and request.method == 'POST':

        # Get/check files from AJAX request
        shp_files = request.FILES.getlist('shapefiles')

        for shp_file in shp_files:
            file_name = shp_file.name
            if file_name.endswith('.shp'):
                shp_file_object = shp_file
                filename = file_name
            elif file_name.endswith('.dbf'):
                dbf_file_object = shp_file
            elif file_name.endswith('.shx'):
                shx_file_obejct = shp_file
            elif file_name.endswith('.prj'):
                prj_file_content = shp_file.read()

    elif request.is_ajax() and request.method == 'GET':
        try:
            res_id = request.GET['res_id']
            print "res_id: %s" % res_id
            # hs = get_oauth_hs(request)
            hs = HydroShare()
            hs.getResource(res_id, destination=hs_tempdir, unzip=True)
            res_contents_dir = os.path.join(hs_tempdir, res_id, res_id, 'data', 'contents')
            print "res_contents_dir: %s" % res_contents_dir
            if os.path.exists(res_contents_dir):
                for file_name in os.listdir(res_contents_dir):
                    if file_name.endswith('.shp'):
                        shp_file_object = open(os.path.join(res_contents_dir, file_name))
                        filename = file_name
                    elif file_name.endswith('.dbf'):
                        dbf_file_object = open(os.path.join(res_contents_dir, file_name))
                    elif file_name.endswith('.shx'):
                        shx_file_obejct = open(os.path.join(res_contents_dir, file_name))
                    elif file_name.endswith('.prj'):
                        prj_file_content = open(os.path.join(res_contents_dir, file_name)).read()

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

    '''
    Credit: The following code was adapted from https://gist.github.com/frankrowe/6071443
    '''
    # Read the shapefile-like object
    shp_reader = shapefile.Reader(shp=shp_file_object, dbf=dbf_file_object, shx=shx_file_obejct)
    fields = shp_reader.fields[1:]
    field_names = [field[0] for field in fields]
    shp_buffer = []
    for sr in shp_reader.shapeRecords():
        atr = dict(zip(field_names, sr.record))
        geom = sr.shape.__geo_interface__
        shp_buffer.append(dict(type="Feature", geometry=geom, properties=atr))

    shp_file_object.close()
    dbf_file_object.close()
    shx_file_obejct.close()

    # Write the GeoJSON object
    geojson = dumps({"type": "FeatureCollection", "features": shp_buffer}, indent=2) + "\n"
    '''
    End credit
    '''

    if res_id:
        if os.path.exists(os.path.join(hs_tempdir, res_id)):
            shutil.rmtree(os.path.join(hs_tempdir, res_id))

    return JsonResponse({
        'success': 'Files uploaded successfully.',
        'geojson': geojson,
        'projection': prj_file_content,
        'filename': filename
    })


def get_hs_res_list(request):
    if request.is_ajax() and request.method == 'GET':
        valid_res_list = []

        # hs = get_oauth_hs(request)
        hs = HydroShare()
        for resource in hs.getResourceList():
            if resource['resource_type'] == 'GeographicFeatureResource' \
                    or resource['resource_type'] == 'RasterResource':

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


def get_oauth_hs(request):
    global hs_hostname

    client_id = getattr(settings, "SOCIAL_AUTH_HYDROSHARE_KEY", "None")
    client_secret = getattr(settings, "SOCIAL_AUTH_HYDROSHARE_SECRET", "None")

    # Throws django.core.exceptions.ObjectDoesNotExist if current user is not signed in via HydroShare OAuth
    token = request.user.social_auth.get(provider='hydroshare').extra_data['token_dict']
    auth = HydroShareAuthOAuth2(client_id, client_secret, token=token)

    return HydroShare(auth=auth, hostname=hs_hostname)


def get_json_response(response_type, message):
    return JsonResponse({response_type: message})
