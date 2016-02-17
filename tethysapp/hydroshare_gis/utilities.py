from hs_restclient import HydroShare, HydroShareAuthOAuth2
from django.http import JsonResponse
from django.conf import settings
from tethys_sdk.services import get_spatial_dataset_engine

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


def store_file_on_geoserver(res_id, res_type, res_path_or_obj, is_zip):
    global geoserver_name, workspace_id, uri
    result = None

    # First get an engine
    engine = get_spatial_dataset_engine(name=geoserver_name)

    # Create a workspace named after our app
    if not engine.get_workspace(workspace_id)['success']:
        engine.create_workspace(workspace_id=workspace_id, uri=uri)

    store_id = 'res_%s' % res_id
    full_store_id = '%s:%s' % (workspace_id, store_id)

    if res_type == 'RasterResource':
        result = engine.create_coverage_resource(store_id=full_store_id,
                                                 coverage_file=res_path_or_obj,
                                                 overwrite=True)

    elif res_type == 'GeographicFeatureResource':
        if is_zip is True:
            result = engine.create_shapefile_resource(store_id=full_store_id,
                                                      shapefile_zip=res_path_or_obj,
                                                      overwrite=True)
        else:
            print res_path_or_obj
            result = engine.create_shapefile_resource(store_id=full_store_id,
                                                      shapefile_upload=res_path_or_obj,
                                                      overwrite=True)

    # Check if it was successful
    if result:
        if not result['success']:
            raise Exception()
        else:
            layer_name = engine.list_resources(store=store_id)['result'][0]
            layer_id = '%s:%s' % (workspace_id, layer_name)
            return layer_name, layer_id



