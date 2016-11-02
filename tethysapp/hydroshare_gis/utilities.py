from django.http import JsonResponse
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from tethys_sdk.services import get_spatial_dataset_engine
from django.core.exceptions import ObjectDoesNotExist
from model import Layer

import hs_restclient as hs_r
# from geoserver.catalog import FailedRequestError

import requests
# from requests import auth
import zipfile
import os
import sqlite3
import xmltodict
# import shutil
from datetime import datetime
from tempfile import TemporaryFile
from json import dumps, loads
from inspect import getfile, currentframe
from sys import exc_info
from traceback import format_exception
from socket import gethostname
from subprocess import check_output
from StringIO import StringIO
from mimetypes import guess_type

workspace_id = None
spatial_dataset_engine = None
currently_testing = False

def get_oauth_hs(request):
    hs = None
    hs_hostname = 'www.hydroshare.org'
    try:
        client_id = getattr(settings, 'SOCIAL_AUTH_HYDROSHARE_KEY', 'None')
        client_secret = getattr(settings, 'SOCIAL_AUTH_HYDROSHARE_SECRET', 'None')
        token = request.user.social_auth.get(provider='hydroshare').extra_data['token_dict']
        auth = hs_r.HydroShareAuthOAuth2(client_id, client_secret, token=token)
        hs = hs_r.HydroShare(auth=auth, hostname=hs_hostname)
    except ObjectDoesNotExist:
        if '127.0.0.1' in request.get_host() or 'localhost' in request.get_host():
            auth = hs_r.HydroShareAuthBasic(username='test', password='test')
            hs = hs_r.HydroShare(auth=auth, hostname=hs_hostname)
    return hs


def get_json_response(response_type, message):
    return JsonResponse({response_type: message})


def upload_file_to_geoserver(res_id, res_type, res_file, file_index=None):
    return_obj = {
        'success': False,
        'message': None,
        'results': {
            'layer_name': None,
            'layer_id': None
        }
    }
    response = None
    results = return_obj['results']
    engine = return_spatial_dataset_engine()
    store_id = res_id
    full_store_id = '%s:%s' % (get_workspace(), store_id)
    is_zip = zipfile.is_zipfile(res_file)

    try:
        if res_type == 'RasterResource':
            is_image_pyramid = check_if_image_pyramid(res_file)
            coverage_type = 'imagepyramid' if is_image_pyramid else 'geotiff'
            if file_index:
                store_id = '%s_%s' % (res_id, file_index)
                full_store_id = '%s:%s' % (get_workspace(), store_id)

            coverage_name = store_id if is_zip else None

            # Creates a resource from a file stored directly on the GeoServer
            # url = '{0}/rest/workspaces/{1}/coveragestores/{2}/external.{3}'.format(get_geoserver_url(), get_workspace(), res_id,
            #                                                               coverage_type)
            # data = 'file:///var/lib/geoserver/data/data/{workspace}/test/utah_ned301.tif'.format(workspace=get_workspace())
            #
            # headers = {
            #     "Content-type": 'text/plain'
            # }
            #
            # r = requests.put(url=url,
            #         files=None,
            #         data=data,
            #         headers=headers,
            #         auth=auth.HTTPBasicAuth(username=get_geoserver_credentials()[0],
            #                            password=get_geoserver_credentials()[1]))

            response = engine.create_coverage_resource(store_id=full_store_id,
                                                       coverage_file=res_file,
                                                       coverage_type=coverage_type,
                                                       coverage_name=coverage_name,
                                                       overwrite=True,
                                                       debug=get_debug_val())

        elif res_type == 'GeographicFeatureResource':
            if file_index:
                store_id = '%s_%s' % (res_id, file_index)
                full_store_id = '%s:%s' % (get_workspace(), store_id)

            if is_zip is True:
                response = engine.create_shapefile_resource(store_id=full_store_id,
                                                            shapefile_zip=res_file,
                                                            overwrite=True,
                                                            debug=get_debug_val())
            elif type(res_file) is not unicode:
                response = engine.create_shapefile_resource(store_id=full_store_id,
                                                            shapefile_upload=res_file,
                                                            overwrite=True,
                                                            debug=get_debug_val())
            else:
                response = engine.create_shapefile_resource(store_id=full_store_id,
                                                            shapefile_base=str(res_file),
                                                            overwrite=True,
                                                            debug=get_debug_val())

        if response:
            if not response['success']:
                try:
                    result = engine.create_workspace(workspace_id=get_workspace(),
                                                     uri='tethys_app-%s' % get_workspace(),
                                                     debug=get_debug_val())
                    if not result['success']:
                        raise Exception
                    else:
                        return_obj = upload_file_to_geoserver(res_id, res_type, res_file, file_index)
                except Exception as e:
                    e.message = response['error']
                    raise
            else:
                try:
                    layer_name = response['result']['name']
                except KeyError:
                    r = engine.list_resources(store=store_id, workspace=get_workspace(), debug=get_debug_val())
                    layer_name = r['result'][-1]

                results['layer_name'] = layer_name
                results['layer_id'] = '%s:%s' % (get_workspace(), layer_name)
                results['store_id'] = store_id
                return_obj['success'] = True
        else:
            raise Exception
    except AttributeError:
        engine.delete_store(store_id=store_id, purge=True, recurse=True, debug=get_debug_val())
        engine.create_workspace(workspace_id=get_workspace(),
                                uri='tethys_app-%s' % get_workspace(),
                                debug=get_debug_val())
        return_obj = upload_file_to_geoserver(res_id, res_type, res_file, file_index)

    return return_obj


def zip_files(res_files, zip_path):
    return_obj = {
        'success': False
    }

    if not os.path.exists(zip_path):
        if not os.path.exists(os.path.dirname(zip_path)):
            os.mkdir(os.path.dirname(zip_path))

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, False) as zip_object:
        if type(res_files) is list:
            for f in res_files:
                zip_object.write(f, os.path.basename(f))
        elif type(res_files) == UploadedFile:
            zip_object.writestr(os.path.basename(res_files), res_files.read())
        else:
            zip_object.write(res_files, os.path.basename(res_files))
        zip_object.close()

    return_obj['success'] = True

    return return_obj


def return_spatial_dataset_engine():
    global spatial_dataset_engine
    if spatial_dataset_engine is None:
        spatial_dataset_engine = get_spatial_dataset_engine(name='default')

    return spatial_dataset_engine


def get_layer_md_from_geoserver(store_id, layer_name, res_type):
    response_obj = {
        'success': False,
        'message': None,
        'attributes': None,
        'extents': None,
        'geom_type': None
    }

    geom_type = None
    geoserver_url = get_geoserver_url()

    if res_type == 'GeographicFeatureResource':
        url = '{0}/rest/workspaces/{1}/datastores/{2}/featuretypes/{3}.json'.format(geoserver_url,
                                                                                    get_workspace(),
                                                                                    store_id,
                                                                                    layer_name)
    else:
        url = '{0}/rest/workspaces/{1}/coveragestores/{2}/coverages/{3}.json'.format(geoserver_url,
                                                                                     get_workspace(),
                                                                                     store_id,
                                                                                     layer_name)

    r = requests.get(url, auth=get_geoserver_credentials())
    if r.status_code != 200:
        response_obj['message'] = 'The Geoserver appears to be down.'
    else:
        json = r.json()

        if res_type == 'GeographicFeatureResource':
            try:
                extents = json['featureType']['latLonBoundingBox']
            except KeyError:
                extents = json['featureType']['nativeBoundingBox']


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

    return response_obj


def get_geoserver_url(request=None):
    engine = return_spatial_dataset_engine()
    geoserver_url = engine.endpoint.split('/rest')[0]

    if request:
        return JsonResponse({'geoserver_url': geoserver_url})
    else:
        return geoserver_url


def get_debug_val():
    global currently_testing
    val = False
    if gethostname() == 'ubuntu':
        if not currently_testing:
            val = True

    return val


def extract_site_info_from_time_series(sqlite_fpath):
    site_info = None
    with sqlite3.connect(sqlite_fpath) as con:
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


def extract_site_info_from_hs_metadata(hs, res_id):
    site_info = None
    try:
        md_dict = xmltodict.parse(hs.getScienceMetadata(res_id))
        if len(md_dict['rdf:RDF']['rdf:Description'][0]['dc:coverage']) == 1:
            site_info_list = md_dict['rdf:RDF']['rdf:Description'][0]['dc:coverage']['dcterms:point']['rdf:value'].split(';')
        else:
            site_info_list = md_dict['rdf:RDF']['rdf:Description'][0]['dc:coverage'][0]['dcterms:point']['rdf:value'].split(';')
        lon = None
        lat = None
        projection = None
        for item in site_info_list:
            if 'north' in item:
                lat = float(item.split('=')[1])
            elif 'east' in item:
                lon = float(item.split('=')[1])
            elif 'projection' in item:
                projection = item.split('=')[1]
        site_info = {
            'lon': lon,
            'lat': lat,
            'projection': projection
        }
    except KeyError:
        pass

    return site_info


def sizeof_fmt(num, suffix='B'):
    for unit in ['bytes', 'k', 'M', 'G', 'T', 'P', 'E', 'Z']:
        if abs(num) < 1024.0:
            if unit == 'bytes':
                return "%3.1f %s" % (num, unit)
            return "%3.1f %s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def make_geoserver_request(web_service, params):
    geoserver_url = get_geoserver_url() + '/%s' % web_service

    r = requests.get(geoserver_url, params=params, auth=get_geoserver_credentials())

    return r


def get_band_info(hs, res_id, res_type, raster_fpath=None):
    band_info = None
    if res_type == 'RasterResource':
        try:
            md_dict = xmltodict.parse(hs.getScienceMetadata(res_id))
            band_info_raw = md_dict['rdf:RDF']['rdf:Description'][0]['hsterms:BandInformation']['rdf:Description']
            band_info = {}
            if 'hsterms:minimumValue' in band_info_raw:
                band_info['min'] = float(band_info_raw['hsterms:minimumValue'])
            if 'hsterms:maximumValue' in band_info_raw:
                band_info['max'] = float(band_info_raw['hsterms:maximumValue'])
            if 'hsterms:noDataValue' in band_info_raw:
                band_info['nd'] = float(band_info_raw['hsterms:noDataValue'])
            if 'hsterms:variableName' in band_info_raw:
                band_info['variable'] = str(band_info_raw['hsterms:variableName'])
            if 'hsterms:variableUnit' in band_info_raw:
                band_info['units'] = str(band_info_raw['hsterms:variableUnit'])

        except KeyError:
            pass
        except Exception as e:
            print 'Unexpected, though not fatal, error occurred in get_band_info while processing res: %s' % res_id
            print str(e)

        if band_info is None and raster_fpath and os.path.exists(raster_fpath):
            band_info = extract_band_info_from_file(raster_fpath)

    return band_info


def get_geoserver_credentials():
    engine = return_spatial_dataset_engine()
    return (engine.username, engine.password)


def process_local_file(file_list, proj_id, hs, username):
    return_obj = {
        'success': False,
        'message': None,
        'results': {
            'res_id': None,
            'res_type': None,
            'layer_name': None,
            'layer_id': None,
            'layer_extents': None,
            'layer_attributes': None,
            'site_info': None,
            'geom_type': None,
            'band_info': None,
            'project_info': None,
            'public_fname': None
        }
    }
    results = return_obj['results']
    res_type = None
    res_id = proj_id
    res_files = None
    hs_tempdir = get_hs_tempdir(username)

    for f in file_list:
        file_name = f.name
        if file_name.endswith('.shp'):
            results['layer_name'] = os.path.splitext(file_name)[0]
            res_type = 'GeographicFeatureResource'
            res_files = file_list
            break
        elif file_name.endswith('.tif'):
            results['layer_name'] = os.path.splitext(file_name)[0]
            res_type = 'RasterResource'
            res_files = os.path.join(hs_tempdir, res_id, file_name[:-4] + '.zip')
            zip_files(f, res_files)
            break
        elif file_name.endswith('.zip'):
            res_zip = os.path.join(hs_tempdir, res_id, file_name)
            if not os.path.exists(res_zip):
                if not os.path.exists(os.path.dirname(res_zip)):
                    os.mkdir(os.path.dirname(res_zip))
            with zipfile.ZipFile(res_zip, 'w', zipfile.ZIP_DEFLATED, False) as zip_object:
                with zipfile.ZipFile(StringIO(f.read())) as z:
                    for file_name in z.namelist():
                        zip_object.writestr(file_name, z.read(file_name))
                        if file_name.endswith('.shp'):
                            results['layer_name'] = os.path.splitext(file_name)[0]
                            res_type = 'GeographicFeatureResource'
                        elif file_name.endswith('.tif'):
                            results['layer_name'] = os.path.splitext(file_name)[0]
                            res_type = 'RasterResource'

            res_files = os.path.join(hs_tempdir, res_id, file_name)

    if res_type is not None:
        results['res_type'] = res_type

        check_res = upload_file_to_geoserver(res_id, res_type, res_files)
        if not check_res['success']:
            return_obj['message'] = check_res['message']
        else:
            r = check_res['results']
            layer_name = r['layer_name']
            results['layer_id'] = r['layer_id']
            store_id = r['store_id']

            response = get_layer_md_from_geoserver(store_id=store_id, layer_name=layer_name,
                                                   res_type=res_type)
            if not response['success']:
                results['message'] = response['message']
            else:
                results['layer_attributes'] = response['attributes']
                results['layer_extents'] = response['extents']
                results['geom_type'] = response['geom_type']

                for f in file_list:
                    tempfile = '/tmp/hs_gis_files/' + f.name
                    with open(tempfile, 'w+') as res_file:
                        for chunk in f.chunks():
                            res_file.write(chunk)

                    hs.addResourceFile(pid=proj_id, resource_file=tempfile)
                    if os.path.exists(tempfile):
                        os.remove(tempfile)
                return_obj['success'] = True
    else:
        return_obj['message'] = 'Unrecognized filetype was uploaded. Layer not added.'


    return return_obj


def get_hs_res_object(hs, res_id, res_type=None, res_title=None, username=None):
    return_obj = {
        'success': False,
        'message': None,
        'results': []
    }

    '''
        Each result in results has these options
        {
                'res_id': res_id,
                'res_type': res_type,
                'layer_name': res_title,
                'layer_id': None,
                'layer_extents': None,
                'layer_attributes': None,
                'geom_type': None,
                'band_info': None,
                'site_info': None,
                'project_info': None,
                'public_fname': None
        }
    '''

    res_layers_obj_list = get_res_layers_from_db(hs, res_id, res_type, res_title, username)
    if res_layers_obj_list:
        return_obj['results'] = res_layers_obj_list
        return_obj['success'] = True

    else:
        return_obj = process_hs_res(hs, res_id, res_type, res_title, username)

    return return_obj


def process_hs_res(hs, res_id, res_type=None, res_title=None, username=None):
    global currently_testing
    return_obj = {
        'success': False,
        'message': None,
        'results': []
    }

    results = return_obj['results']
    hs_tempdir = get_hs_tempdir(username)

    try:
        if res_type is None or res_title is None:
            md = hs.getSystemMetadata(res_id)
            res_type = md['resource_type']
            res_title = md['resource_title']

        response = process_res_by_type(hs, res_id, res_type, hs_tempdir)
        return_obj['message'] = response['message']
        if response['success']:
            for r in response['results']:
                result = {
                    'res_id': res_id,
                    'res_type': r['res_type'] if 'res_type' in r else res_type,
                    'layer_name': r['layer_name'] if ('layer_name' in r and r['layer_name'] is not None) else res_title,
                    'layer_id': r['layer_id'] if 'layer_id' in r else None,
                    'layer_extents': r['layer_extents'] if 'layer_extents' in r else None,
                    'layer_attributes': r['layer_attributes'] if 'layer_attributes' in r else None,
                    'geom_type': r['geom_type'] if 'geom_type' in r else None,
                    'band_info': r['band_info'] if 'band_info' in r else None,
                    'site_info': r['site_info'] if 'site_info' in r else None,
                    'project_info': r['project_info'] if 'project_info' in r else None,
                    'public_fname': r['public_fname'] if 'public_fname' in r else None,
                    'res_mod_date': get_res_mod_date(hs, res_id)
                }
                results.append(result)

                param_obj = prepare_result_for_layer_db(result)
                Layer.add_layer_to_database(**param_obj)
            return_obj['success'] = True

    except hs_r.HydroShareHTTPException:
        return_obj['message'] = 'The HydroShare server appears to be down.'
    except hs_r.HydroShareNotFound:
        return_obj['message'] = 'This resource was not found on www.hydroshare.org'
    except hs_r.HydroShareNotAuthorized:
        return_obj['message'] = 'You are not authorized to access this resource.'
    except Exception as e:
        if gethostname() == 'ubuntu':
            exc_type, exc_value, exc_traceback = exc_info()
            msg = e.message if e.message else str(e)
            print ''.join(format_exception(exc_type, exc_value, exc_traceback))
            print msg
            return_obj['message'] = 'An unexpected error ocurred: %s' % msg
        else:
            return_obj['message'] = 'An unexpected error ocurred. App admin has been notified.'
            if not currently_testing:
                msg = e.message if e.message else ''
                msg += '\nHost: %s \nResource ID: %s \nUser: %s' % (gethostname(), res_id, hs.getUserInfo()['username'])
                email_admin('Error Report', traceback=exc_info(), custom_msg=msg)

    os.system('rm -rf %s' % hs_tempdir)

    return return_obj


def download_res_from_hs(hs, res_id, tempdir):
    return_obj = {
        'success': False,
        'message': None,
        'res_contents_path': None
    }
    TOO_BIG_PREFIXES = ['G', 'T', 'P', 'E', 'Z']
    is_too_big = False
    res_size = 0
    for res_file in hs.getResourceFileList(res_id):
        res_size += res_file['size']

    for prefix in TOO_BIG_PREFIXES:
        if prefix in sizeof_fmt(res_size):
            is_too_big = True
            break

    if not is_too_big:
        hs.getResource(res_id, destination=tempdir, unzip=True)
        res_contents_path = os.path.join(tempdir, res_id, res_id, 'data', 'contents')
        return_obj['res_contents_path'] = res_contents_path
        return_obj['success'] = True
    else:
        return_obj['message'] = 'This resource is too large to open in HydroShare GIS.'

    return return_obj


def process_res_by_type(hs, res_id, res_type, hs_tempdir):
    return_obj = {
        'success': False,
        'message': None,
        'results': []
    }
    '''
    Each result in results has these options
    {
            'layer_name': None,
            'res_type': res_type,
            'project_info': None,
            'layer_id': None,
            'band_info': None,
            'site_info': None,
            'layer_attributes': None,
            'layer_extents': None,
            'geom_type': None,
            'public_fname': None
    }
    '''
    results = return_obj['results']

    if res_type == 'RefTimeSeriesResource':
        site_info = extract_site_info_from_hs_metadata(hs, res_id)
        if not site_info:
            return_obj['message'] = 'Resource contains insufficient geospatial information.'
        else:
            result = {
                'res_type': res_type,
                'site_info': site_info,
            }
            results.append(result)
            return_obj['success'] = True
    else:
        response = download_res_from_hs(hs, res_id, hs_tempdir)
        if not response['success']:
            return_obj['message'] = response['message']
        else:
            res_contents_path = response['res_contents_path']
            response = get_info_from_res_files(res_id, res_type, res_contents_path)
            return_obj['message'] = response['message']
            if response['success']:
                error_occurred = False
                for r in response['results']:
                    res_filepath = r['res_filepath'] if 'res_filepath' in r else None
                    res_type = r['res_type'] if 'res_type' in r else None
                    layer_name = r['layer_name'] if 'layer_name' in r else None
                    public_fname = r['public_fname'] if 'public_fname' in r else None

                    if res_type == 'GenericResource':
                        if res_filepath and res_filepath.endswith('mapProject.json'):
                            with open(res_filepath) as project_file:
                                project_info = project_file.read()
                            result = {
                                'res_type': res_type,
                                'project_info': project_info
                            }
                            results.append(result)
                            break
                        else:
                            result = {
                                'res_type': res_type,
                                'public_fname': public_fname,
                                'layer_name': layer_name,
                                'site_info': extract_site_info_from_hs_metadata(hs, res_id)
                            }
                            results.append(result)
                    elif res_type == 'GeographicFeatureResource' or res_type == 'RasterResource':
                        check_res = upload_file_to_geoserver(res_id, res_type, res_filepath)
                        if not check_res['success']:
                            error_occurred = True
                            return_obj['message'] = check_res['message']
                            break
                        else:
                            response = check_res['results']
                            geoserver_layer_name = response['layer_name']
                            layer_id = response['layer_id']
                            store_id = response['store_id']

                            response = get_layer_md_from_geoserver(store_id=store_id, layer_name=geoserver_layer_name,
                                                                   res_type=res_type)
                            if not response['success']:
                                error_occurred = True
                                return_obj['message'] = response['message']
                                break
                            else:
                                result = {
                                    'layer_name': layer_name,
                                    'res_type': res_type,
                                    'layer_id': layer_id,
                                    'layer_attributes': response['attributes'],
                                    'layer_extents': response['extents'],
                                    'geom_type': response['geom_type'],
                                    'band_info': get_band_info(hs, res_id, res_type),
                                    'public_fname': public_fname
                                }
                                results.append(result)
                    else:
                        error_occurred = True
                        return_obj['message'] = 'Resource cannot be opened with HydroShare GIS: Invalid resource type.'

                if not error_occurred:
                    return_obj['success'] = True

    return return_obj

def get_info_from_res_files(res_id, res_type, res_contents_path):
    return_obj = {
        'success': False,
        'message': None,
        'results': [],
    }
    '''
    Each result in 'results' has the following options
    {
            'res_filepath': None,
            'res_type': res_type,
            'layer_name': None
    }
    '''
    results = return_obj['results']

    if os.path.exists(res_contents_path):
        res_files_list = os.listdir(res_contents_path)

        if res_type == 'GeographicFeatureResource':
            for f in res_files_list:
                src = os.path.join(res_contents_path, f)
                public_fpath = os.path.join(res_contents_path, res_id + os.path.splitext(f)[1])
                os.rename(src, public_fpath)
            res_fpath = os.path.join(res_contents_path, res_id)
            prj_path = res_fpath + '.prj'
            r = check_crs(res_type, prj_path)
            return_obj['message'] = r['message'] % os.path.basename(prj_path) if r['message'] else None
            if r['success'] and r['crsWasChanged']:
                with open(prj_path, 'w') as f:
                    f.seek(0)
                    f.write(r['new_wkt'])
                    f.truncate()
            result = {
                'res_filepath': res_fpath,
                'res_type': res_type,
            }
            results.append(result)
        elif res_type == 'RasterResource':
            num_files = len(res_files_list)
            vrt_path = None
            res_fpath = None
            for res_fname in res_files_list:
                fpath = os.path.join(res_contents_path, res_fname)
                if num_files == 2:
                    if res_fname.endswith('.tif'):
                        tmp_fpath = os.path.join(res_contents_path, '%s.tif' % res_id)
                        os.rename(fpath, tmp_fpath)
                        r = check_crs(res_type, tmp_fpath)
                        return_obj['message'] = r['message'] % res_fname if r['message'] else None
                        if not r['success']:
                            return return_obj
                        else:
                            if r['crsWasChanged']:
                                code = r['code']
                                os.system('gdal_edit.py -a_srs {0} {1}'.format(code, tmp_fpath))
                            res_fpath = tmp_fpath.replace('tif', 'zip')
                            zip_files(tmp_fpath, res_fpath)
                            break
                elif res_fname.endswith('.vrt'):
                    vrt_path = fpath
                    break

            if num_files > 2:
                pyramid_dir_path = os.path.join(res_contents_path, '%s/' % res_id)
                res_fpath = '%s.zip' % pyramid_dir_path[:-1]
                os.mkdir(pyramid_dir_path)
                gdal_retile = 'gdal_retile.py -levels 9 -ps 2048 2048 -co "TILED=YES" -targetDir %s %s'
                os.system(gdal_retile % (pyramid_dir_path, vrt_path))
                zip_folder(pyramid_dir_path, res_fpath)

            result = {
                'res_filepath': res_fpath,
                'res_type': res_type,
            }
            results.append(result)

        return_obj['success'] = True

    return return_obj


def get_hs_res_list(hs):
    global currently_testing
    return_obj = {
        'success': False,
        'message': None,
        'res_list': None
    }
    res_list = []

    try:
        valid_res_types = ['GenericResource', 'GeographicFeatureResource', 'RasterResource', 'RefTimeSeriesResource', 'TimeSeriesResource', 'ScriptResource']
        for res in hs.getResourceList(types=valid_res_types):
            res_id = res['resource_id']
            # This code calculates the cummulative files size of each resource. Comment out to improve performance.
            # res_size = 0
            # try:
            #     for res_file in hs.getResourceFileList(res_id):
            #         res_size += res_file['size']
            #
            # except hs_r.HydroShareNotAuthorized:
            #     continue
            # except Exception as e:
            #     print str(e)

            res_list.append({
                'title': res['resource_title'],
                'type': res['resource_type'],
                'id': res_id,
                # 'size': sizeof_fmt(res_size) if res_size != 0 else "N/A",
                'owner': res['creator']
            })

        return_obj['res_list'] = res_list
        return_obj['success'] = True

    except hs_r.HydroShareHTTPException:
        return_obj['message'] = 'The HydroShare server appears to be down.'
    except Exception as e:
        print e
        return_obj['message'] = 'An unexpected error ocurred. App admin has been notified.'
        if gethostname() != 'ubuntu' and not currently_testing:
            email_admin('Error Report', traceback=exc_info())

    return return_obj


def get_workspace():
    global workspace_id
    if workspace_id is None:
        if 'apps.hydroshare' in gethostname():
            workspace_id = 'hydroshare_gis'
        else:
            workspace_id = 'hydroshare_gis_testing'

    return workspace_id


def get_hs_tempdir(username=None, file_index=None):
    hs_tempdir = '/tmp/hs_gis_files/%s' % (('%s/' % username) if username else '')
    if file_index is not None:
        hs_tempdir = os.path.join(hs_tempdir, str(file_index))
    if not os.path.exists(hs_tempdir):
        os.makedirs(hs_tempdir)

    return hs_tempdir

def get_public_tempdir(username=None):
    public_tempdir = os.path.join(getfile(currentframe()).replace('utilities.py', 'public/temp/'),
                                  username if username else '')

    if not os.path.exists(public_tempdir):
        os.makedirs(public_tempdir)

    return public_tempdir


def email_admin(subject, traceback=None, custom_msg=None):
    if traceback is None and custom_msg is None:
        return -1

    subject = 'HydroShare GIS: %s' % subject
    msg = ''
    if traceback:
        exc_type, exc_value, exc_traceback = traceback
        trcbck = ''.join(format_exception(exc_type, exc_value, exc_traceback))
        msg += trcbck
    if custom_msg:
        msg += custom_msg
    requests.post(
        "https://api.mailgun.net/v3/sandbox5d62ce2f0725460bb5eab88b496fd2a6.mailgun.org/messages",
        auth=("api", "key-6eee015c8a719e4510a093cabf7bdfd4"),
        data={
            "from": "Mailgun Sandbox <postmaster@sandbox5d62ce2f0725460bb5eab88b496fd2a6.mailgun.org>",
            "to": "progrummer@gmail.com",
            "subject": subject,
            "text": msg
        }
    )


def check_crs(res_type, fpath):
    return_obj = {
        'success': False,
        'message': None,
        'code': None,
        'crsWasChanged': False,
        'new_wkt': None
    }
    if res_type == 'RasterResource':
        gdal_info = check_output('gdalinfo %s' % fpath, shell=True)
        start = 'Coordinate System is:'
        length = len(start)
        end = 'Origin ='
        if gdal_info.find(start) == -1:
            print "NO PROJECTION INFO ASSOCIATED WITH FILE. WILL ATTEMPT TO FORCE TO EPSG 3857"
            return_obj['message'] = 'The file %s has no projection (coordinate reference system) info associated with it. ' \
                                    'An attempt has still been made to display it by assuming an EPSG:3857 projection.'
            return_obj['crsWasChanged'] = True
            return_obj['code'] = 'EPSG:3857'
            return_obj['success'] = True
            return return_obj
        start_index = gdal_info.find(start) + length
        end_index = gdal_info.find(end)
        crs_raw = gdal_info[start_index:end_index]
        crs = ''.join(crs_raw.split())
    else:
        with open(fpath) as f:
            crs = f.read()

    endpoint = 'http://prj2epsg.org/search.json'
    params = {
        'mode': 'wkt',
        'terms': crs
    }
    crs_is_unknown = True
    flag_unhandled_error = False
    try:
        while crs_is_unknown:
            r = requests.get(endpoint, params=params)
            if '50' in str(r.status_code):
                raise Exception
            elif r.status_code == 200:
                response = r.json()
                print response
                raw_input("PAUSED")
                if 'errors' in response:
                    errs = response['errors']
                    if 'Invalid WKT syntax' in errs:
                        err = errs.split(':')[2]
                        if err and 'Parameter' in err:
                            crs_param = err.split('"')[1]
                            rm_indx_start = crs.find(crs_param)
                            rm_indx_end = None
                            sub_str = crs[rm_indx_start:]
                            counter = 0
                            check = False
                            for i, c in enumerate(sub_str):
                                if c == '[':
                                    counter += 1
                                    check = True
                                elif c == ']':
                                    counter -= 1
                                    check = True
                                if check:
                                    if counter == 0:
                                        rm_indx_end = i + rm_indx_start + 1
                                        break
                            crs = crs[:rm_indx_start] + crs[rm_indx_end:]
                            if ',' in crs[:-4]:
                                i = crs.rfind(',')
                                crs = crs[:i] + crs[i+1:]
                            params['terms'] = crs
                        else:
                            flag_unhandled_error = True
                    else:
                        flag_unhandled_error = True
                else:
                    crs_is_unknown = False
                    codes = response['codes']
                    # If there are no codes in the result, a match wasn't found. In that case, an attempt will still be
                    # made to add the layer to GeoServer since this still works in some cases.
                    if len(codes) != 0:
                        if res_type == 'RasterResource':
                            code = codes[0]['code']
                            if code not in crs:
                                return_obj['crsWasChanged'] = True
                            return_obj['code'] = 'EPSG:' + code
                        else:
                            r = requests.get(response['codes'][0]['url'])
                            proj_json = r.json()
                            raw_wkt = proj_json['wkt']
                            tmp_list = []
                            for seg in raw_wkt.split('\n'):
                                tmp_list.append(seg.strip())
                            return_obj['new_wkt'] = ''.join(tmp_list)

                    return_obj['success'] = True

                if flag_unhandled_error:
                    return_obj['message'] = 'The file "%s" was not added due to erroneous or incomplete ' \
                                            'projection (coordinate reference system) information.'
                    break
            else:
                params['mode'] = 'keywords'
                continue
    except Exception as e:
        e.message = 'A service that HydroShare GIS depends on currently appears to be down. An app admin has been notified to further investigate.'
        raise

    return return_obj


def delete_tempfiles(username):
    hs_tempdir = get_hs_tempdir(username)
    os.system('rm -rf %s' % hs_tempdir)



def save_new_project(hs, project_info, res_title, res_abstract, res_keywords, username):
    return_obj = {
        'success': False,
        'message': None,
        'res_id': None
    }
    res_id = None
    hs_tempdir = get_hs_tempdir(username)

    try:
        res_type = 'GenericResource'
        fname = 'mapProject.json'
        project_info_json = loads(project_info)
        orig_id = project_info_json['resId']

        with TemporaryFile() as f:
            f.write(dumps(project_info_json))
            f.seek(0)
            res_id = hs.createResource(res_type,
                                       res_title,
                                       resource_file=f,
                                       resource_filename=fname,
                                       keywords=res_keywords,
                                       abstract=res_abstract
                                       )
            project_info_json['resId'] = res_id
            f.seek(0)
            f.write(dumps(project_info_json))
            f.truncate()
            f.seek(0)
            hs.deleteResourceFile(res_id, fname)
            hs.addResourceFile(pid=res_id, resource_file=f, resource_filename=fname)

        if orig_id:
            r = download_res_from_hs(hs, orig_id, hs_tempdir)
            if not r['success']:
                return_obj['message'] = r['message']
            else:
                res_contents_path = r['res_contents_path']
                res_files_list = os.listdir(res_contents_path)
                if len(res_files_list) > 1:
                    os.remove(os.path.join(res_contents_path, fname))
                    res_list = [os.path.join(res_contents_path, f) for f in res_files_list]
                    for f in res_list:
                        hs.addResourceFile(pid=res_id, resource_file=f)

                    return_obj['success'] = 'Resource created successfully.'
                    return_obj['res_id'] = res_id
        else:
            return_obj['success'] = 'Resource created successfully.'
            return_obj['res_id'] = res_id
    except Exception as e:
        print str(e)
        if res_id:
            hs.deleteResource(pid=res_id)
        return_obj['error'] = 'An unknown/unexpected error was encountered. Project not saved.'

    return return_obj


def zip_folder(folder_path, output_path):
    """Zip the contents of an entire folder (with that folder included
    in the archive). Empty subfolders will be included in the archive
    as well.
    """

    parent_folder = os.path.dirname(folder_path)
    contents = os.walk(folder_path)
    with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for root, folders, files in contents:
            for folder_name in folders:
                absolute_path = os.path.join(root, folder_name)
                relative_path = absolute_path.replace(parent_folder + '/', '')
                zip_file.write(absolute_path, relative_path)
            for file_name in files:
                absolute_path = os.path.join(root, file_name)
                relative_path = absolute_path.replace(parent_folder + '/', '')
                zip_file.write(absolute_path, relative_path)


def save_project(hs, res_id, project_info):
    return_obj = {
        'success': False,
        'message': None
    }
    try:
        fname = 'mapProject.json'

        hs.deleteResourceFile(res_id, fname)

        with TemporaryFile() as f:
            f.write(project_info)
            f.seek(0)
            hs.addResourceFile(res_id, f, fname)
        return_obj['success'] = True

    except Exception as e:
        print str(e)
        return_obj['message'] = 'An unknown/unexpected error was encountered. Project not saved.'

    return return_obj

def generate_attribute_table(layer_id, layer_attributes):
    return_obj = {
        'success': False,
        'message': None,
        'feature_properties': None
    }
    try:
        params = {
            'service': 'wfs',
            'version': '2.0.0',
            'request': 'GetFeature',
            'typeNames': layer_id,
            'propertyName': layer_attributes,
            'outputFormat': 'application/json'
        }

        r = make_geoserver_request('wfs', params)
        json = r.json()

        feature_properties = []

        features = json['features']
        for feature in features:
            feature_properties.append(feature['properties'])
        return_obj['feature_properties'] = dumps(feature_properties)
        return_obj['success'] = True
    except Exception as e:
        return_obj['message'] = str(e)

    return return_obj


# def get_generic_files(hs, res_dict_string, username):
#     return_obj = {
#         'success': False,
#         'message': None,
#     }
#     res_dict = loads(res_dict_string)
#     public_tempdir = get_public_tempdir(username)
#     for res in res_dict:
#         for res_file in res_dict[res]:
#             hs.getResourceFile(res, res_file, destination=public_tempdir)
#         return_obj['success'] = True
# 
#     return return_obj


def set_currently_testing(val):
    global currently_testing
    currently_testing = val


def get_features_on_click(params_str):
    params = loads(params_str)
    r = make_geoserver_request('wms', params)
    return r.json()


def prepare_result_for_layer_db(result):

    result.pop('project_info', None)  # parameter "project_info" not expected in following call

    # The values of the following keys, if they are not None, are python object that must converted to strings
    result['layer_extents'] = dumps(result['layer_extents']) if result['layer_extents'] else None
    result['band_info'] = dumps(result['band_info']) if result['band_info'] else None
    result['site_info'] = dumps(result['site_info']) if result['site_info'] else None

    return result


def get_res_mod_date(hs, res_id):
    date_modified = None
    md_dict = xmltodict.parse(hs.getScienceMetadata(res_id))

    try:
        for date_obj in md_dict['rdf:RDF']['rdf:Description'][0]['dc:date']:
            if 'dcterms:modified' in date_obj:
                date_modified = date_obj['dcterms:modified']['rdf:value']
    except Exception as e:
        print str(e)

    return date_modified


def res_has_been_updated(db_date, res_date):
    db_date_obj = datetime.strptime(db_date.split('+')[0], '%Y-%m-%dT%X.%f')
    res_date_obj = datetime.strptime(res_date.split('+')[0], '%Y-%m-%dT%X.%f')
    if db_date_obj < res_date_obj:
        return True

    return False


def get_res_files_list(hs, res_id):
    return_obj = {
        'success': False,
        'message': None,
        'results': {}
    }

    sorted_res_files_list = []
    full_name_list = []
    name_list = []
    size_list = []
    req_shp_file_exts = ['.shp', '.prj', '.shx', '.dbf']
    all_shp_file_exts = req_shp_file_exts + ['.sbn', '.sbx', '.cpg', '.xml']
    rem_shp_file_exts = all_shp_file_exts[:]
    rem_shp_file_exts.remove('.shp')
    files_processed_list = []

    try:
        res_file_dict_list = list(hs.getResourceFileList(res_id))
        for res_file_dict in res_file_dict_list:
            full_name_list.append(os.path.basename(res_file_dict['url']))

        for res_file_dict in res_file_dict_list:
            basename = os.path.basename(res_file_dict['url'])
            splitext = os.path.splitext(basename)
            name = splitext[0]
            ext = splitext[1]
            size = res_file_dict['size']
            if basename not in files_processed_list:
                if ext in all_shp_file_exts:
                    has_shp = '%s.shp' % name in full_name_list
                    has_dbf = '%s.dbf' % name in full_name_list
                    has_prj = '%s.prj' % name in full_name_list
                    has_shx = '%s.shx' % name in full_name_list

                    if has_shp and has_dbf and has_prj and has_shx:
                        shp_file = '%s.shp' % name

                        for fext in rem_shp_file_exts:  # Add all associated shapefiles to files_processed_list
                            f1 = "%s%s" % (name, fext)
                            f2 = "%s%s" % (shp_file, fext)  # This is to catch the .shp.xml file if it exists

                            if f1 in full_name_list:
                                files_processed_list.append(f1)
                            elif f2 in full_name_list:
                                files_processed_list.append(f2)

                        if ext != '.shp':
                            continue

                name_list.append(basename)
                size_list.append(size)

        name_size_list = zip(name_list, size_list)
        name_size_list_sorted = sorted(name_size_list, key=lambda tup: tup[1])

        for item in name_size_list_sorted:
            sorted_res_files_list.append(item[0])

        return_obj['results']['generic_res_files_list'] = sorted_res_files_list
        return_obj['success'] = True

    except hs_r.HydroShareHTTPException:
        return_obj['message'] = 'The HydroShare server appears to be down.'
    except hs_r.HydroShareNotFound:
        return_obj['message'] = 'This resource was not found on www.hydroshare.org'
    except hs_r.HydroShareNotAuthorized:
        return_obj['message'] = 'You are not authorized to access this resource.'
    except Exception as e:
        if gethostname() == 'ubuntu':
            exc_type, exc_value, exc_traceback = exc_info()
            msg = e.message if e.message else str(e)
            print ''.join(format_exception(exc_type, exc_value, exc_traceback))
            print msg
            return_obj['message'] = 'An unexpected error ocurred: %s' % msg
        else:
            return_obj['message'] = 'An unexpected error ocurred. App admin has been notified.'
            if not currently_testing:
                msg = e.message if e.message else ''
                msg += '\nHost: %s \nResource ID: %s \nUser: %s' % (gethostname(), res_id, hs.getUserInfo()['username'])
                email_admin('Error Report', traceback=exc_info(), custom_msg=msg)

    return return_obj


def get_res_layers_from_db(hs, res_id, res_type, res_title, username):
    res_layers = []
    db_res_layers = Layer.get_layers_by_associated_res_id(res_id)

    if db_res_layers:
        for res_layer in db_res_layers:
            flag_reload_layer = res_has_been_updated(res_layer.res_mod_date, get_res_mod_date(hs, res_id))
            if flag_reload_layer:
                Layer.remove_layer_by_res_id(res_id)
                res_layers = process_hs_res(hs, res_id, res_type, res_title, username)
                break
            else:
                res_layer = {
                    'res_id': res_id,
                    'res_type': res_layer.associated_res_type,
                    'layer_name': res_layer.name,
                    'layer_id': res_layer.layer_id,
                    'layer_extents': loads(res_layer.extents) if res_layer.extents else None,
                    'layer_attributes': res_layer.attributes,
                    'geom_type': res_layer.geom_type,
                    'band_info': loads(res_layer.band_info) if res_layer.band_info else None,
                    'site_info': loads(res_layer.site_info) if res_layer.site_info else None,
                    'public_fname': res_layer.associated_file_name
                }
                res_layers.append(res_layer)

    return res_layers


def get_res_layer_obj_from_generic_file(hs, res_id, res_file_name, username, file_index):
    return_obj = {
        'success': False,
        'message': None,
        'results': None
    }
    '''
    Each result has these key/value pairs
    {
            'layer_name': None,
            'res_type': res_type,
            'project_info': None,
            'layer_id': None,
            'band_info': None,
            'site_info': None,
            'layer_attributes': None,
            'layer_extents': None,
            'geom_type': None,
            'public_fname': None
    }
    '''

    hs_tempdir = get_hs_tempdir(username, file_index)
    layer_id = None
    layer_attributes = None
    layer_extents = None
    geom_type = None
    band_info = None
    site_info = None
    project_info = None

    try:

        response = get_info_from_generic_res_file(hs, res_id, res_file_name, hs_tempdir, file_index)
        return_obj['message'] = response['message']
        if response['success']:
            results = response['results']
            res_filepath = results['res_filepath'] if 'res_filepath' in results else None
            res_type = results['res_type'] if 'res_type' in results else None
            layer_name = results['layer_name'] if 'layer_name' in results else None
            public_fname = results['public_fname'] if 'public_fname' in results else None

            if res_type == 'GenericResource':

                if res_filepath and res_filepath.endswith('mapProject.json'):
                    with open(res_filepath) as project_file:
                        project_info = project_file.read()
                else:
                    site_info = extract_site_info_from_hs_metadata(hs, res_id)

            elif res_type == 'GeographicFeatureResource' or res_type == 'RasterResource':

                check_res = upload_file_to_geoserver(res_id, res_type, res_filepath, file_index)

                if not check_res['success']:
                    return_obj['message'] = check_res['message']
                else:
                    response = check_res['results']
                    geoserver_layer_name = response['layer_name']
                    layer_id = response['layer_id']
                    store_id = response['store_id']

                    response = get_layer_md_from_geoserver(store_id=store_id, layer_name=geoserver_layer_name,
                                                           res_type=res_type)
                    if not response['success']:
                        return_obj['message'] = response['message']
                    else:
                        layer_attributes = response['attributes']
                        layer_extents = response['extents']
                        geom_type = response['geom_type']

                        band_info_tif_path = os.path.join(hs_tempdir, '{0}_{1}.tif'.format(res_id, file_index))
                        band_info = get_band_info(hs, res_id, res_type, band_info_tif_path)

            results = {
                'res_id': res_id,
                'res_type': res_type,
                'layer_name': layer_name,
                'layer_id': layer_id,
                'layer_extents': layer_extents,
                'layer_attributes': layer_attributes,
                'geom_type': geom_type,
                'band_info': band_info,
                'site_info': site_info,
                'project_info': project_info,
                'public_fname': public_fname,
                'res_mod_date': get_res_mod_date(hs, res_id)
            }

            if not project_info:
                param_obj = prepare_result_for_layer_db(results)
                Layer.add_layer_to_database(**param_obj)

            return_obj['results'] = results
            return_obj['success'] = True

    except hs_r.HydroShareHTTPException:
        return_obj['message'] = 'The HydroShare server appears to be down.'
    except hs_r.HydroShareNotFound:
        return_obj['message'] = 'This resource was not found on www.hydroshare.org'
    except hs_r.HydroShareNotAuthorized:
        return_obj['message'] = 'You are not authorized to access this resource.'
    except Exception as e:
        if gethostname() == 'ubuntu':
            exc_type, exc_value, exc_traceback = exc_info()
            msg = e.message if e.message else str(e)
            print ''.join(format_exception(exc_type, exc_value, exc_traceback))
            print msg
            return_obj['message'] = 'An unexpected error ocurred: %s' % msg
        else:
            return_obj['message'] = 'An unexpected error ocurred. App admin has been notified.'
            if not currently_testing:
                msg = e.message if e.message else ''
                msg += '\nHost: %s \nResource ID: %s \nUser: %s' % (gethostname(), res_id, hs.getUserInfo()['username'])
                email_admin('Error Report', traceback=exc_info(), custom_msg=msg)

    return return_obj


def get_info_from_generic_res_file(hs, res_id, res_file_name, hs_tempdir, file_index):
    return_obj = {
        'success': False,
        'message': None,
        'results': None,
    }
    '''
    Each result in 'results' has the following options
    {
            'res_filepath': None,
            'res_type': res_type,
            'layer_name': None
    }
    '''

    res_fpath = os.path.join(hs_tempdir, res_file_name)
    res_type = 'GenericResource'

    if res_file_name == 'mapProject.json':
        hs.getResourceFile(res_id, res_file_name, destination=hs_tempdir)
        results = {
            'res_filepath': res_fpath,
            'res_type': res_type,
            'layer_name': None
        }
    else:
        req_shp_file_exts = ['.shp', '.prj', '.shx', '.dbf']
        kml_exts = ['.kml', '.kmz']
        tif_exts = ['.tif', '.vrt']
        is_full_generic = False
        fpath = os.path.join(hs_tempdir, res_file_name)
        fname_and_ext = os.path.splitext(res_file_name)
        fname = fname_and_ext[0]
        fext = fname_and_ext[1]

        if fext in kml_exts:
            hs.getResourceFile(res_id, res_file_name, destination=hs_tempdir)
            # Openlayers KML Implementation
            if fext == '.kmz':
                os.system('unzip -q -d %s %s' % (hs_tempdir, fpath))
                kml_path = os.path.join(hs_tempdir, 'doc.kml')
            else:
                kml_path = fpath

            shp_fname = '%s_%s.shp' % (res_id, file_index)
            shp_output_path = os.path.join(hs_tempdir, shp_fname)

            os.system('ogr2ogr -f "ESRI Shapefile" {0} {1}'.format(shp_output_path, kml_path))

            if os.path.exists(shp_output_path):
                res_fpath = os.path.splitext(shp_output_path)[0]
                res_type = 'GeographicFeatureResource'

        elif fext == '.shp':
            is_shapefile = True
            try:
                for ext in req_shp_file_exts:
                    hs.getResourceFile(res_id, '%s%s' % (fname, ext), destination=hs_tempdir)
            except hs_r.HydroShareNotFound:
                is_shapefile = False

            if is_shapefile:
                shp_file_paths = []

                for ext in req_shp_file_exts:
                    path = os.path.join(hs_tempdir, '%s%s' % (fname, ext))
                    # Rename files to res_id base
                    tmp_fpath = os.path.join(hs_tempdir,
                                             '%s_%s%s' % (res_id, file_index, ext))
                    os.rename(path, tmp_fpath)
                    shp_file_paths.append(tmp_fpath)

                # Rename zip to res_id base just to be safe
                res_fpath = os.path.join(hs_tempdir,
                                         '%s_%s.zip' % (res_id, file_index))

                zip_files(shp_file_paths, res_fpath)
                res_type = 'GeographicFeatureResource'

            else:
                is_full_generic = True

        elif fext in tif_exts:
            hs.getResourceFile(res_id, res_file_name, destination=hs_tempdir)
            res_type = 'RasterResource'
            tmp_fpath = os.path.join(hs_tempdir, '%s_%s.tif' % (res_id, file_index))
            os.rename(fpath, tmp_fpath)
            r = check_crs(res_type, tmp_fpath)
            return_obj['message'] = r['message'] % res_file_name
            if not r['success']:
                return return_obj
            else:
                if r['crsWasChanged']:
                    code = r['code']
                    os.system('gdal_edit.py -a_srs {0} {1}'.format(code, tmp_fpath))
                res_fpath = tmp_fpath.replace('tif', 'zip')
                zip_files(tmp_fpath, res_fpath)
        else:
            is_full_generic = True

        if is_full_generic:
            res_fpath = None  # Generic resource files rely on public_fname, not res_filepath

        results = {
            'public_fname': res_file_name,
            'res_filepath': res_fpath,
            'res_type': res_type,
            'layer_name': res_file_name,
        }

    return_obj['results'] = results
    return_obj['success'] = True

    return return_obj


def extract_band_info_from_file(raster_fpath):
    from gdal import Open
    from gdalconst import GA_ReadOnly
    from numpy import allclose as numpy_allclose

    raster_dataset = Open(raster_fpath, GA_ReadOnly)

    # get raster band count
    if raster_dataset:
        band_info = {}
        band_count = raster_dataset.RasterCount

        if band_count == 1:
            band = raster_dataset.GetRasterBand(1)
            minimum, maximum, _, _ = band.ComputeStatistics(False)
            no_data = band.GetNoDataValue()
            new_no_data = None

            if no_data and numpy_allclose(minimum, no_data):
                new_no_data = minimum
            elif no_data and numpy_allclose(maximum, no_data):
                new_no_data = maximum

            if new_no_data is not None:
                band.SetNoDataValue(new_no_data)
                minimum, maximum, _, _ = band.ComputeStatistics(False)

            units = band.GetUnitType()
            nd = band.GetNoDataValue()
            band_info = {
                'variable': 'Unknown',
                'units': units if units else 'Unknown',
                'nd': nd if nd else 'Unknown',
                'max': maximum if maximum else 'Unknown',
                'min': minimum if minimum else 'Unknown',
            }
    else:
        band_info = None

    return band_info

def check_if_image_pyramid(fpath):
    is_image_pyramid = False
    with zipfile.ZipFile(fpath, 'r') as z:
        for fname in z.namelist():
            if fname.endswith('/'):
                is_image_pyramid = True

    return is_image_pyramid


def get_file_mime_type(file_name):
    # The mimetypes module can't find all mime types
    file_format_type = guess_type(file_name)[0]
    if not file_format_type:
        file_format_type = 'application/%s' % os.path.splitext(file_name)[1][1:]

    return file_format_type