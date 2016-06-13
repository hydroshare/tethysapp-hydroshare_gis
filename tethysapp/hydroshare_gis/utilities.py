from hs_restclient import HydroShare, HydroShareAuthOAuth2, HydroShareAuthBasic
from django.http import JsonResponse
from django.conf import settings
from tethys_sdk.services import get_spatial_dataset_engine
from django.core.exceptions import ObjectDoesNotExist

import requests
import zipfile
import os
import sqlite3
import xmltodict


geoserver_name = 'default'
workspace_id = 'hydroshare_gis'


def get_oauth_hs(request):
    hs_hostname = 'www.hydroshare.org' if 'apps.hydroshare' in request.get_host() else 'playground.hydroshare.org'

    client_id = getattr(settings, 'SOCIAL_AUTH_HYDROSHARE_KEY', 'None')
    client_secret = getattr(settings, 'SOCIAL_AUTH_HYDROSHARE_SECRET', 'None')

    # Throws django.core.exceptions.ObjectDoesNotExist if current user is not signed in via HydroShare OAuth
    token = request.user.social_auth.get(provider='hydroshare').extra_data['token_dict']
    auth = HydroShareAuthOAuth2(client_id, client_secret, token=token)

    return HydroShare(auth=auth, hostname=hs_hostname)


def get_json_response(response_type, message):
    return JsonResponse({response_type: message})


def upload_file_to_geoserver(res_id, res_type, res_file, is_zip, is_mosaic, try_again=True):
    global workspace_id
    result = None

    engine = return_spatial_dataset_engine()

    store_id = 'res_%s' % res_id
    full_store_id = '%s:%s' % (workspace_id, store_id)

    if res_type == 'RasterResource':
        print 'res_id: %s' % res_id
        print 'res_type: %s' % res_type
        print 'res_file: %s' % res_file
        print 'is_zip: %s' % is_zip
        print 'is_mosaic: %s' % is_mosaic
        coverage_type = 'imagemosaic' if is_mosaic else 'geotiff'
        result = engine.create_coverage_resource(store_id=full_store_id,
                                                 coverage_file=res_file,
                                                 coverage_type=coverage_type,
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
            if 'already exists in namespace' in result['error'] and try_again and type(res_file) is unicode:
                if os.path.exists(res_file):
                    dir_name = os.path.dirname(res_file)
                    file_name = os.path.basename(res_file)
                    file_parts = os.path.splitext(file_name)
                    new_file_name = file_parts[0] + '(1)' + file_parts[1]
                    new_file_path = os.path.join(dir_name, new_file_name)
                    os.rename(res_file, new_file_path)
                    return upload_file_to_geoserver(res_id, res_type, new_file_path, is_zip, is_mosaic, False)
            else:
                return {
                    'success': False,
                    'message': result['error']
                }
        else:
            layer_name = engine.list_resources(store=store_id)['result'][0]
            layer_id = '%s:%s' % (workspace_id, layer_name)
            return {
                'success': True,
                'layer_name': layer_name,
                'layer_id': layer_id
            }
    else:
        return {
            'success': False,
            'message': 'Upload to geoserver failed for some reason.'
        }


def make_file_zipfile(res_files, filename, zip_path):
    if not os.path.exists(zip_path):
        if not os.path.exists(os.path.dirname(zip_path)):
            os.mkdir(os.path.dirname(zip_path))

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, False) as zip_object:
        if type(res_files) is list:
            for each_file in res_files:
                if len(res_files) > 1 and not each_file.endswith('.tif'):
                    zip_object.write(each_file, filename + os.path.splitext(each_file)[1])
                else:
                    zip_object.write(each_file, os.path.basename(each_file))
        else:
            zip_object.writestr(filename, res_files.read())
        zip_object.close()


def return_spatial_dataset_engine():
    global geoserver_name, workspace_id
    try:
        engine = get_spatial_dataset_engine(name=geoserver_name)
        workspace = engine.get_workspace(workspace_id)
        if not workspace['success']:
            print "WORKSPACE DOES NOT EXIST AND MUST BE CREATED"
            engine.create_workspace(workspace_id=workspace_id, uri='tethys_app-hydroshare_gis')
    except Exception as e:
        print str(e)
        engine = None

    return engine


def get_layer_extents_and_attributes(res_id, layer_name, res_type):
    geom_type = None
    geoserver_url = get_geoserver_url()

    if res_type == 'GeographicFeatureResource':
        url = geoserver_url + '/rest/workspaces/hydroshare_gis/datastores/res_' + res_id + \
              '/featuretypes/' + layer_name + '.json'
    else:
        url = geoserver_url + '/rest/workspaces/hydroshare_gis/coveragestores/res_' + res_id + \
              '/coverages/' + layer_name + '.json'

    r = requests.get(url, auth=get_credentials(geoserver_url))
    json = r.json()

    if res_type == 'GeographicFeatureResource':
        extents = json['featureType']['latLonBoundingBox']

        attributes = json['featureType']['attributes']['attribute']
        attributes_string = ''
        for attribute in attributes:
            if attribute['name'] == 'the_geom':
                geom_type = attribute['binding'].split('.')[-1]
            else:
                attributes_string += attribute['name'] + ','
    else:
        extents = json['coverage']['latLonBoundingBox']
        attributes_string = ','

    return extents, attributes_string[:-1], geom_type


def get_geoserver_url(request=None):
    engine = get_spatial_dataset_engine(name=geoserver_name)
    geoserver_url = engine.endpoint.split('/rest')[0]

    if request:
        return JsonResponse({'geoserver_url': geoserver_url})
    else:
        return geoserver_url


def extract_site_info_from_time_series(sqlite_file_path):
    site_info = None
    with sqlite3.connect(sqlite_file_path) as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute('SELECT * FROM Sites')
        site = cur.fetchone()
        if site:
            if site['Latitude'] and site['Longitude']:
                site_info = {'lon': site['Longitude'], 'lat': site['Latitude'], 'units': 'Decimal degrees'}
                if site['SpatialReferenceID']:
                    cur.execute('SELECT * FROM SpatialReferences WHERE SpatialReferenceID=?',
                                (site['SpatialReferenceID'],))
                    spatialref = cur.fetchone()
                    if spatialref:
                        if spatialref['SRSName']:
                            site_info['projection'] = spatialref['SRSName']

    return site_info


def extract_site_info_from_ref_time_series(hs, res_id):
    try:
        md_dict = xmltodict.parse(hs.getScienceMetadata(res_id))
        site_info_list = md_dict['rdf:RDF']['rdf:Description'][0]['dc:coverage'][0]['dcterms:point']['rdf:value'].split(';')
        lon = float(site_info_list[0].split('=')[1])
        lat = float(site_info_list[1].split('=')[1])
        projection = site_info_list[2].split('=')[1]
        site_info = {
            'lon': lon,
            'lat': lat,
            'projection': projection
        }
    except Exception as e:
        print str(e)
        site_info = None
    return site_info


def sizeof_fmt(num, suffix='B'):
    for unit in ['bytes', 'k', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            if unit == 'bytes':
                return "%3.1f %s" % (num, unit)
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def request_wfs_info(params):
    geoserver_url = get_geoserver_url()
    geoserver_url += '/wfs'

    r = requests.get(geoserver_url, params=params, auth=get_credentials(geoserver_url))

    return r

def get_hs_object(request):
    try:
        hs = get_oauth_hs(request)
    except ObjectDoesNotExist as e:
        print str(e)
        auth = HydroShareAuthBasic(username='scrawley', password='rebound1')
        hs_hostname = 'www.hydroshare.org' if 'apps.hydroshare' in request.get_host() else 'playground.hydroshare.org'
        hs = HydroShare(hostname=hs_hostname, auth=auth)
    return hs


def get_band_info(hs, res_id):
    try:
        md_dict = xmltodict.parse(hs.getScienceMetadata(res_id))
        band_info_raw = md_dict['rdf:RDF']['rdf:Description'][0]['hsterms:BandInformation']['rdf:Description']
        band_info = {
            'min': float(band_info_raw['hsterms:minimumValue']),
            'max': float(band_info_raw['hsterms:maximumValue']),
            'nd': float(band_info_raw['hsterms:noDataValue'])
        }
    except Exception as e:
        print str(e)
        band_info = None
    return band_info


def get_credentials(geoserver_url):
    username = 'admin'
    password = 'geoserver' if 'appsdev' in geoserver_url else 'hydroshare'
    return (username, password)
