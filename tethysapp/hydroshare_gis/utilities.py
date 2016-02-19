import zipfile

from django.core.files.uploadedfile import TemporaryUploadedFile
from hs_restclient import HydroShare, HydroShareAuthOAuth2
from django.http import JsonResponse
from django.conf import settings
from tethys_sdk.services import get_spatial_dataset_engine

import os

hs_hostname = 'www.hydroshare.org'
geoserver_name = 'localhost_geoserver'
geoserver_url = 'http://127.0.0.1:8181/geoserver/wms'
workspace_id = 'hydroshare_gis'
uri = 'http://127.0.0.1:8000/apps/hydroshare-gis'


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


def upload_file_to_geoserver(res_id, res_type, res_file, is_zip):
    global geoserver_name, workspace_id, uri
    result = None

    engine = return_spatial_dataset_engine()

    store_id = 'res_%s' % res_id
    full_store_id = '%s:%s' % (workspace_id, store_id)

    if res_type == 'RasterResource':
        result = engine.create_coverage_resource(store_id=full_store_id,
                                                 coverage_file=res_file,
                                                 coverage_type='geotiff',
                                                 overwrite=True)

    elif res_type == 'GeographicFeatureResource':
        if is_zip is True:
            result = engine.create_shapefile_resource(store_id=full_store_id,
                                                      shapefile_zip=res_file,
                                                      overwrite=True)
        elif type(res_file) is not unicode:
            result = engine.create_shapefile_resource(store_id=full_store_id,
                                                      shapefile_upload=res_file,
                                                      overwrite=True)
        else:
            result = engine.create_shapefile_resource(store_id=full_store_id,
                                                      shapefile_base=str(res_file),
                                                      overwrite=True)

    # Check if it was successful
    if result:
        if not result['success']:
            raise Exception()
        else:
            layer_name = engine.list_resources(store=store_id)['result'][0]
            layer_id = '%s:%s' % (workspace_id, layer_name)
            return layer_name, layer_id


def create_zipfile_from_file(res_file, filename, zip_path):
    if not os.path.exists(zip_path):
        if not os.path.exists(os.path.dirname(zip_path)):
            os.mkdir(os.path.dirname(zip_path))
        else:
            with open(zip_path, 'w') as f:
                f.close()
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, False) as zip_object:
        if type(res_file) is not TemporaryUploadedFile:
            zip_object.write(res_file)
        else:
            zip_object.writestr(filename, res_file.read())
        zip_object.close()


def return_spatial_dataset_engine():
    global geoserver_name, workspace_id, uri
    print 'geoserver_name: %s' % geoserver_name
    print 'workspace_id: %s' % workspace_id
    print 'uri: %s' % uri
    engine = get_spatial_dataset_engine(name=geoserver_name)
    if not engine.get_workspace(workspace_id)['success']:
        print 'Workspace does not exist and must be created'
        engine.create_workspace(workspace_id=workspace_id, uri=uri)
    return engine
