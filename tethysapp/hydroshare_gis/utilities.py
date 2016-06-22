from hs_restclient import HydroShare, HydroShareAuthOAuth2, HydroShareNotAuthorized, HydroShareAuthBasic
from django.http import JsonResponse
from django.conf import settings
from tethys_sdk.services import get_spatial_dataset_engine
from django.core.exceptions import ObjectDoesNotExist

import requests
import zipfile
import os
import sqlite3
import xmltodict
import shutil

geoserver_name = 'default'
workspace_id = 'hydroshare_gis'
hs_tempdir = '/tmp/hs_gis_files/'


def get_oauth_hs(request):
    hs = None
    hs_hostname = 'www.hydroshare.org'
    try:
        client_id = getattr(settings, 'SOCIAL_AUTH_HYDROSHARE_KEY', 'None')
        client_secret = getattr(settings, 'SOCIAL_AUTH_HYDROSHARE_SECRET', 'None')

        # Throws django.core.exceptions.ObjectDoesNotExist if current user is not signed in via HydroShare OAuth
        token = request.user.social_auth.get(provider='hydroshare').extra_data['token_dict']
        auth = HydroShareAuthOAuth2(client_id, client_secret, token=token)
        hs = HydroShare(auth=auth, hostname=hs_hostname)
    except ObjectDoesNotExist:
        if '127.0.0.1' in request.get_host() or 'localhost' in request.get_host():
            auth = HydroShareAuthBasic(username='test', password='test')
            hs = HydroShare(auth=auth, hostname=hs_hostname)
    return hs


def get_json_response(response_type, message):
    return JsonResponse({response_type: message})


def upload_file_to_geoserver(res_id, res_type, res_file, is_zip, is_mosaic):
    return_obj = {
        'success': False,
        'message': None,
        'results': {
            'layer_name': None,
            'layer_id': None
        }
    }
    global workspace_id
    result = None
    results = return_obj['results']
    try:
        engine = return_spatial_dataset_engine()
        if engine is None:
            return_obj['message'] = 'No spatial dataset engine was returned'
        else:
            store_id = 'res_%s' % res_id
            full_store_id = '%s:%s' % (workspace_id, store_id)

            if res_type == 'RasterResource':
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
            if result:
                if not result['success']:
                    return_obj['message'] = result['error']
                else:
                    layer_name = engine.list_resources(store=store_id, debug=True)['result'][0]
                    results['layer_name'] = layer_name
                    results['layer_id'] = '%s:%s' % (workspace_id, layer_name)
                    return_obj['success'] = True
            else:
                return_obj['message'] = 'Failed while uploading resource to Geoserver: Unkown error'
    except Exception as e:
        print str(e)
        return_obj['message'] = 'Failed while uploading resource to Geoserver: %s' % str(e)

    return return_obj


def make_zipfile(res_files, filename, zip_path):
    return_obj = {'success': False}
    try:
        if not os.path.exists(zip_path):
            if not os.path.exists(os.path.dirname(zip_path)):
                os.mkdir(os.path.dirname(zip_path))

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, False) as zip_object:
            if type(res_files) is list:
                for f in res_files:
                    if len(res_files) > 1 and not f.endswith('.tif'):
                        zip_object.write(f, filename + os.path.splitext(f)[1])
                    else:
                        zip_object.write(f, os.path.basename(f))
            else:
                zip_object.writestr(filename, res_files.read())
            zip_object.close()

        return_obj['success'] = True
    except Exception as e:
        return_obj['message'] = 'Process failed with the following error while zipping resource files: %s' % str(e)

    return return_obj


def return_spatial_dataset_engine():
    global geoserver_name, workspace_id
    try:
        engine = get_spatial_dataset_engine(name=geoserver_name)
        workspace = engine.get_workspace(workspace_id)
        if not workspace['success']:
            engine.create_workspace(workspace_id=workspace_id, uri='tethys_app-hydroshare_gis')
    except Exception as e:
        print str(e)
        engine = None

    return engine


def get_layer_md_from_geoserver(res_id, layer_name, res_type):
    response_obj = {'success': False}

    try:
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
        response_obj = {
            'success': True,
            'attributes': attributes_string[:-1],
            'extents': extents,
            'geom_type': geom_type
        }
    except Exception as e:
        response_obj['message'] = 'An error occurred while executing get_layer_md_from_geoserver: %s' % str(e)

    return response_obj


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


def get_band_info(hs, res_id, res_type):
    band_info = None
    if res_type == 'RasterResource':
        try:
            md_dict = xmltodict.parse(hs.getScienceMetadata(res_id))
            band_info_raw = md_dict['rdf:RDF']['rdf:Description'][0]['hsterms:BandInformation']['rdf:Description']
            band_info = {
                'min': float(band_info_raw['hsterms:minimumValue']),
                'max': float(band_info_raw['hsterms:maximumValue']),
                'nd': float(band_info_raw['hsterms:noDataValue'])
            }
        except KeyError:
            pass
        except Exception as e:
            print str(e)

    return band_info


def get_credentials(geoserver_url):
    username = 'admin'
    password = 'geoserver' if 'appsdev' in geoserver_url else 'hydroshare'
    return (username, password)


# def process_local_file(request):
#     res_type = None
#     res_id = None
#
#     if not os.path.exists(hs_tempdir):
#         os.mkdir(hs_tempdir)
#
#     file_list = request.FILES.getlist('files')
#     file_name = None
#     for f in file_list:
#         file_name = f.name
#         if file_name.endswith('.shp'):
#             # res_id = str(file_name[:-4].__hash__())
#             res_type = 'GeographicFeatureResource'
#             res_filepath_or_obj = file_list
#             break
#         elif file_name.endswith('.tif'):
#             # res_id = str(file_name[:-4].__hash__())
#             res_id = 'temp_id'
#             res_type = 'RasterResource'
#             res_filepath_or_obj = os.path.join(hs_tempdir, res_id, file_name[:-4] + '.zip')
#             make_zipfile(f, file_name, res_filepath_or_obj)
#             break
#         elif file_name.endswith('.zip'):
#             is_zip = True
#             res_id = 'temp_id'
#             res_zip = os.path.join(hs_tempdir, res_id, file_name)
#             if not os.path.exists(res_zip):
#                 if not os.path.exists(os.path.dirname(res_zip)):
#                     os.mkdir(os.path.dirname(res_zip))
#             with zipfile.ZipFile(res_zip, 'w', zipfile.ZIP_DEFLATED, False) as zip_object:
#                 with zipfile.ZipFile(StringIO(f.read())) as z:
#                     for file_name in z.namelist():
#                         zip_object.writestr(file_name, z.read(file_name))
#                         if file_name.endswith('.shp'):
#                             res_id = str(file_name[:-4].__hash__())
#                             res_type = 'GeographicFeatureResource'
#                         elif file_name.endswith('.tif'):
#                             res_id = str(file_name[:-4].__hash__())
#                             res_type = 'RasterResource'
#             os.rename(os.path.join(hs_tempdir, 'temp_id'), os.path.join(hs_tempdir, res_id))
#             res_filepath_or_obj = os.path.join(hs_tempdir, res_id, file_name)
#
#     if res_type is not None:
#         hs = get_oauth_hs(request)
#         if hs is None:
#             return get_json_response('error', 'Please sign in with your HydroShare account to access this feature.')
#         abstract = 'This resource was created while using the HydroShare GIS App.'
#         res_id = hs.createResource(
#             'GenericResource',
#             os.path.splitext(file_name)[0],
#             resource_file=res_filepath_or_obj if res_type == 'RasterResource' else file_list,
#             resource_filename=file_name,
#             abstract=abstract)
#     else:
#         return JsonResponse({
#             'error': 'Zipfile did not contain valid files.'
#         })

def process_hs_res(hs, res_id, res_type=None, res_title=None):
    return_obj = {
        'success': False,
        'message': None,
        'results': {
            'res_id': res_id,
            'res_type': res_type,
            'layer_name': res_title,
            'layer_id': None,
            'layer_extents': None,
            'layer_attributes': None,
            'site_info': None,
            'geom_type': None,
            'band_info': None,
            'project_info': None
        }
    }
    results = return_obj['results']

    try:
        if res_type is None or res_title is None:
            md = hs.getSystemMetadata(res_id)
            res_type = md['resource_type']
            res_title = md['resource_title']
            results['layer_name'] = res_title
            results['res_type'] = res_type

        store_id = 'res_%s' % res_id
        check_res = check_geoserver_for_res(store_id)
        if check_res['isOnGeoserver']:
            layer_name = check_res['layer_name']
            results['layer_id'] = '%s:%s' % (workspace_id, layer_name)
            response = get_layer_md_from_geoserver(res_id=res_id, layer_name=layer_name,
                                                   res_type=res_type)
            if not response['success']:
                return_obj['message'] = response['message']
            else:
                results['layer_attributes'] = response['attributes']
                results['layer_extents'] = response['extents']
                results['geom_type'] = response['geom_type']
                results['band_info'] = get_band_info(hs, res_id, res_type)
                return_obj['success'] = True
        else:
            response = process_res_by_type(hs, res_id, res_type)
            if not response['success']:
                return_obj['message'] = response['message']
            else:
                results['res_type'] = response['res_type']
                results['project_info'] = response['project_info']
                results['layer_name'] = response['layer_name']
                results['layer_id'] = response['layer_id']
                results['band_info'] = response['band_info']
                results['site_info'] = response['site_info']
                results['layer_attributes'] = response['attributes']
                results['layer_extents'] = response['extents']
                results['geom_type'] = response['geom_type']
                results['band_info'] = response['band_info']
                return_obj['success'] = True

    except Exception, e:
        if 'Server Error when accessing' in str(e):
            message = 'This resource is currently inaccessible by HydroShare.'
        elif 'was not found' in str(e):
            message = 'This resource was not found on www.hydroshare.org'
        else:
            message = 'An unexpected error was encountered: %s. Resource(s) not added.' % str(e)

        return_obj['message'] = message

    if os.path.exists(os.path.join(hs_tempdir, res_id)):
        shutil.rmtree(os.path.join(hs_tempdir, res_id))

    return return_obj


def check_geoserver_for_res(store_id):
    return_obj = {'isOnGeoserver': False}
    try:
        engine = return_spatial_dataset_engine()
        store = engine.get_store(store_id=store_id)
        if store['success']:
            layer_name = store['result']['name']

            return_obj = {
                'isOnGeoserver': True,
                'layer_name': layer_name,
            }
    except Exception as e:
        print 'Unexpected error encountered:\n%s' % e

    return return_obj


def download_res_from_hs(hs, res_id):
    return_obj = {
        'success': False,
        'res_contents_path': None
    }
    try:
        if not os.path.exists(hs_tempdir):
            os.mkdir(hs_tempdir)
        hs.getResource(res_id, destination=hs_tempdir, unzip=True)
        res_contents_path = os.path.join(hs_tempdir, res_id, res_id, 'data', 'contents')

        return_obj['res_contents_path'] = res_contents_path
        return_obj['success'] = True
    except Exception as e:
        return_obj['message'] = 'Resource failed to download from HydroShare with this error: %s' % str(e)

    return return_obj


def process_res_by_type(hs, res_id, res_type):
    return_obj = {
        'success': False,
        'message': None,
        'res_type': None,
        'project_info': None,
        'layer_name': None,
        'layer_id': None,
        'band_info': None,
        'site_info': None,
        'layer_attributes': None,
        'layer_extents': None,
        'geom_type': None,
    }
    try:
        if res_type == 'RefTimeSeriesResource':
            site_info = extract_site_info_from_ref_time_series(hs, res_id)
            if not site_info:
                return_obj['message'] = 'Required site info data not available.'
            else:
                return_obj['site_info'] = site_info
                return_obj['success'] = True
        else:
            response = download_res_from_hs(hs, res_id)
            if not response['success']:
                return_obj['message'] = response['message']
            else:
                res_contents_path = response['res_contents_path']
                response = get_info_from_res_files(res_contents_path)
                if not response['success']:
                    return_obj['message'] = response['message']
                else:
                    res_filepath = response['res_filepath']
                    is_mosaic = response['is_mosaic']
                    is_zip = response['is_zip']
                    res_type = response['res_type']
                    return_obj['res_type'] = res_type

                    if res_type == 'GenericResource':
                        if res_filepath and res_filepath.endswith('mapProject.json'):
                            with open(res_filepath) as project_file:
                                project_info = project_file.read()

                            return_obj['project_info'] = project_info
                            return_obj['success'] = True
                        else:
                            return_obj['message'] = 'This resource does not contain any content ' \
                                                    'that HydroShare GIS can display.'
                    elif res_type == 'GeographicFeatureResource' or res_type == 'RasterResource':
                        check_res = upload_file_to_geoserver(res_id, res_type, res_filepath, is_zip, is_mosaic)
                        if check_res['success']:
                            layer_name = check_res['layer_name']
                            return_obj['layer_name'] = layer_name
                            return_obj['layer_id'] = check_res['layer_id']

                            response = get_layer_md_from_geoserver(res_id=res_id, layer_name=layer_name,
                                                                   res_type=res_type)
                            if not response['success']:
                                return_obj['message'] = response['message']
                            else:
                                return_obj['layer_attributes'] = response['attributes']
                                return_obj['layer_extents'] = response['extents']
                                return_obj['geom_type'] = response['geom_type']
                                return_obj['band_info'] = get_band_info(hs, res_id, res_type)
                                return_obj['success'] = True
                        else:
                            return_obj['message'] = check_res['message']
                    else:
                        return_obj['message'] = 'Resource cannot be opened with HydroShare GIS: Invalid resource type.'
    except Exception as e:
        print str(e)
        return_obj['message'] = "Unexpected error encounter while processing the resource: %s" % str(e)

    return return_obj

def get_info_from_res_files(res_contents_path):
    return_obj = {
        'success': False,
        'res_filepath': None,
        'res_type': None,
        'is_mosaic': False,
        'is_zip': False
    }
    res_filepath = None
    res_type = None

    try:
        if os.path.exists(res_contents_path):
            coverage_files = []
            for file_name in os.listdir(res_contents_path):
                if file_name.endswith('.shp'):
                    res_filepath = os.path.join(res_contents_path, file_name[:-4])
                    res_type = 'GeographicFeatureResource'
                    break
                if file_name == 'mapProject.json':
                    res_filepath = os.path.join(res_contents_path, file_name)
                    res_type = 'GenericResource'
                    break
                if file_name.endswith('.vrt') or file_name.endswith('.tif'):
                    if file_name.endswith('.vrt'):
                        return_obj['is_mosaic'] = True
                    coverage_files.append(os.path.join(res_contents_path, file_name))
                    res_type = 'RasterResource'

            if coverage_files:
                res_filepath = os.path.join(res_contents_path, 'temp' + '.zip')
                response = make_zipfile(coverage_files, 'temp', res_filepath)
                if not response['success']:
                    return_obj['message'] = response['message']
                else:
                    return_obj['is_zip'] = True

            return_obj['res_filepath'] = res_filepath
            return_obj['res_type'] = res_type
            return_obj['success'] = True
    except Exception as e:
        return_obj['message'] = 'The following error occurred while accessing the resource files: %s' % str(e)

    return return_obj


def get_hs_res_list(hs):
    # print "DELETEING ALL STORES FROM GEOSERVER"
    # engine = return_spatial_dataset_engine()
    # stores = engine.list_stores(workspace_id)
    # for store in stores['result']:
    #     engine.delete_store(store, True, True)
    #     print "Store %s deleted" % store
    res_list = []

    try:
        valid_res_types = ['GeographicFeatureResource', 'RasterResource', 'RefTimeSeriesResource', 'TimeSeriesResource']
        for res in hs.getResourceList(types=valid_res_types):
            res_id = res['resource_id']
            res_size = 0
            try:
                for res_file in hs.getResourceFileList(res_id):
                    res_size += res_file['size']

            except HydroShareNotAuthorized:
                continue
            except Exception as e:
                print str(e)

            res_list.append({
                'title': res['resource_title'],
                'type': res['resource_type'],
                'id': res_id,
                'size': sizeof_fmt(res_size) if res_size != 0 else "N/A",
                'owner': res['creator']
            })

    except Exception as e:
        print 'Error encountered while getting resource list from HydroShare: %s' % str(e)

    return res_list