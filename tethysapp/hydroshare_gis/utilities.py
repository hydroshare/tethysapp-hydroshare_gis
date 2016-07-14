from django.http import JsonResponse
from django.conf import settings
from tethys_sdk.services import get_spatial_dataset_engine
from django.core.exceptions import ObjectDoesNotExist

import hs_restclient as hs_r
from geoserver.catalog import FailedRequestError

import requests
import zipfile
import os
import sqlite3
import xmltodict
import shutil
from tempfile import TemporaryFile
from json import dumps, loads
from inspect import getfile, currentframe
from sys import exc_info
from traceback import format_exception
from socket import gethostname
from subprocess import check_output
from StringIO import StringIO

hs_tempdir = '/tmp/hs_gis_files/'
public_tempdir = getfile(currentframe()).replace('utilities.py', 'public/temp/')
workspace_id = None
spatial_dataset_engine = None


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


def upload_file_to_geoserver(res_id, res_type, res_file, is_zip, is_mosaic):
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
    store_id = 'res_%s' % res_id
    full_store_id = '%s:%s' % (get_workspace(), store_id)

    try:
        if res_type == 'RasterResource':
            coverage_type = 'imagemosaic' if is_mosaic else 'geotiff'
            response = engine.create_coverage_resource(store_id=full_store_id,
                                                       coverage_file=res_file,
                                                       coverage_type=coverage_type,
                                                       overwrite=True,
                                                       debug=get_debug_val())

        elif res_type == 'GeographicFeatureResource':
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
                        return_obj = upload_file_to_geoserver(res_id, res_type, res_file, is_zip, is_mosaic)
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
                return_obj['success'] = True
        else:
            raise Exception
    except AttributeError:
        engine.delete_store(store_id=store_id, purge=True, recurse=True, debug=get_debug_val())
        engine.create_workspace(workspace_id=get_workspace(),
                                uri='tethys_app-%s' % get_workspace(),
                                debug=get_debug_val())
        return_obj = upload_file_to_geoserver(res_id, res_type, res_file, is_zip, is_mosaic)

    return return_obj


def make_zipfile(res_files, zip_path):
    return_obj = {
        'success': False,
        'message': None
    }

    if not os.path.exists(zip_path):
        if not os.path.exists(os.path.dirname(zip_path)):
            os.mkdir(os.path.dirname(zip_path))

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, False) as zip_object:
        if type(res_files) is list:
            for f in res_files:
                zip_object.write(f, os.path.basename(f))
        else:
            zip_object.writestr(os.path.basename(res_files), res_files.read())
        zip_object.close()

    return_obj['success'] = True

    return return_obj


def return_spatial_dataset_engine():
    global spatial_dataset_engine
    if spatial_dataset_engine is None:
        spatial_dataset_engine = get_spatial_dataset_engine(name='default')

    return spatial_dataset_engine


def get_layer_md_from_geoserver(res_id, layer_name, res_type):
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
        url = '{0}/rest/workspaces/{1}/datastores/res_{2}/featuretypes/{3}.json'.format(geoserver_url,
                                                                                        get_workspace(),
                                                                                        res_id,
                                                                                        layer_name)
    else:
        url = '{0}/rest/workspaces/{1}/coveragestores/res_{2}/coverages/{3}.json'.format(geoserver_url,
                                                                                         get_workspace(),
                                                                                         res_id,
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
    val = False
    if gethostname() == 'ubuntu':
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


def extract_site_info_from_ref_time_series(hs, res_id):
    site_info = None
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


def request_wfs_info(params):
    geoserver_url = get_geoserver_url()
    geoserver_url += '/wfs'

    r = requests.get(geoserver_url, params=params, auth=get_geoserver_credentials())

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


def get_geoserver_credentials():
    engine = return_spatial_dataset_engine()
    return (engine.username, engine.password)


def process_local_file(file_list, proj_id, hs):
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
    is_zip = False
    res_files = None

    if not os.path.exists(hs_tempdir):
        os.mkdir(hs_tempdir)

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
            make_zipfile(f, res_files)
            break
        elif file_name.endswith('.zip'):
            is_zip = True
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

        check_res = upload_file_to_geoserver(res_id, res_type, res_files, is_zip, False)
        if not check_res['success']:
            return_obj['message'] = check_res['message']
        else:
            r = check_res['results']
            layer_name = r['layer_name']
            results['layer_id'] = r['layer_id']

            response = get_layer_md_from_geoserver(res_id=res_id, layer_name=layer_name,
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
        return_obj['message'] = 'Filetype that HydroShare GIS does not recognize was uploaded. Layer not added.'


    return return_obj


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
            'project_info': None,
            'public_fname': None
        }
    }
    results = return_obj['results']
    process_res = False

    try:
        if res_type is None or res_title is None:
            md = hs.getSystemMetadata(res_id)
            res_type = md['resource_type']
            res_title = md['resource_title']
            results['layer_name'] = res_title
            results['res_type'] = res_type

        if res_type == 'GeographicFeatureResource' or res_type == 'RasterResource':
            check_res = check_geoserver_for_res(res_id)
            if check_res['isOnGeoserver']:
                layer_name = check_res['layer_name']
                results['layer_id'] = '%s:%s' % (get_workspace(), layer_name)
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
                process_res = True
        else:
            process_res = True

        if process_res:
            response = process_res_by_type(hs, res_id, res_type)
            if not response['success']:
                return_obj['message'] = response['message']
            else:
                results['res_type'] = response['res_type']
                results['project_info'] = response['project_info']
                results['layer_id'] = response['layer_id']
                results['band_info'] = response['band_info']
                results['site_info'] = response['site_info']
                results['layer_attributes'] = response['layer_attributes']
                results['layer_extents'] = response['layer_extents']
                results['geom_type'] = response['geom_type']
                results['public_fname'] = response['public_fname']
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
            custom_msg = e.message if e.message else ''
            custom_msg += '\nHost: %s\nResource ID: %s' % (gethostname(), res_id)
            email_traceback(exc_info(), custom_msg)

    if os.path.exists(os.path.join(hs_tempdir, res_id)):
        shutil.rmtree(os.path.join(hs_tempdir, res_id))

    return return_obj


def check_geoserver_for_res(res_id):
    return_obj = {'isOnGeoserver': False}
    engine = None
    store_id = 'res_%s' % res_id
    try:
        engine = return_spatial_dataset_engine()
        response = engine.list_resources(store=store_id, workspace=get_workspace())
        if response['success']:
            results = response['result']
            assert len(results) == 1
            layer_name = response['result'][0]
            return_obj = {
                'isOnGeoserver': True,
                'layer_name': layer_name,
            }
    except AssertionError:
        if engine is not None:
            engine.delete_store(store_id=store_id, purge=True, recurse=True)
    except FailedRequestError:
        pass

    return return_obj


def download_res_from_hs(hs, res_id):
    return_obj = {
        'success': False,
        'res_contents_path': None
    }
    if not os.path.exists(hs_tempdir):
        os.mkdir(hs_tempdir)
    hs.getResource(res_id, destination=hs_tempdir, unzip=True)
    res_contents_path = os.path.join(hs_tempdir, res_id, res_id, 'data', 'contents')

    return_obj['res_contents_path'] = res_contents_path
    return_obj['success'] = True

    return return_obj


def process_res_by_type(hs, res_id, res_type):
    return_obj = {
        'success': False,
        'message': None,
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

    if res_type == 'RefTimeSeriesResource':
        site_info = extract_site_info_from_ref_time_series(hs, res_id)
        if not site_info:
            return_obj['message'] = 'Resource contains insufficient geospatial information. Resource not added.'
        else:
            return_obj['site_info'] = site_info
            return_obj['success'] = True
    else:
        response = download_res_from_hs(hs, res_id)
        if not response['success']:
            return_obj['message'] = response['message']
        else:
            res_contents_path = response['res_contents_path']
            response = get_info_from_res_files(res_id, res_type, res_contents_path)
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
                    elif res_filepath:
                        return_obj['public_fname'] = os.path.basename(res_filepath)
                        return_obj['success'] = True
                    else:
                        return_obj['message'] = 'This resource does not contain any content ' \
                                                'that HydroShare GIS can display.'
                elif res_type == 'GeographicFeatureResource' or res_type == 'RasterResource':
                    check_res = upload_file_to_geoserver(res_id, res_type, res_filepath, is_zip, is_mosaic)
                    if not check_res['success']:
                        return_obj['message'] = check_res['message']
                    else:
                        results = check_res['results']
                        layer_name = results['layer_name']
                        return_obj['layer_id'] = results['layer_id']

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
                    return_obj['message'] = 'Resource cannot be opened with HydroShare GIS: Invalid resource type.'

    return return_obj

def get_info_from_res_files(res_id, res_type, res_contents_path):
    return_obj = {
        'success': False,
        'res_filepath': None,
        'res_type': res_type,
        'is_mosaic': False,
        'is_zip': False
    }
    res_fpath = None

    if os.path.exists(res_contents_path):
        if res_type == 'GeographicFeatureResource':
            for f in os.listdir(res_contents_path):
                src = os.path.join(res_contents_path, f)
                dst = os.path.join(res_contents_path, 'res_' + res_id + os.path.splitext(f)[1])
                os.rename(src, dst)
            res_fpath = os.path.join(res_contents_path, 'res_' + res_id)
            prj_path = res_fpath + '.prj'
            r = check_crs(res_type, prj_path)
            if r['success'] and r['crsWasChanged']:
                with open(prj_path, 'w') as f:
                    f.seek(0)
                    f.write(r['new_wkt'])
                    f.truncate()
        elif res_type == 'RasterResource':
            coverage_files = []
            tif_count = 0
            for fname in os.listdir(res_contents_path):
                fpath = os.path.join(res_contents_path, fname)
                if fname.endswith('.tif'):
                    tif_count += 1
                    new_fpath = os.path.join(res_contents_path, 'res_%s_%s.tif' % (res_id, tif_count))
                    os.rename(fpath, new_fpath)
                    fpath = new_fpath
                    r = check_crs(res_type, fpath)
                    if not r['success']:
                        return_obj['message'] = r['message']
                        return return_obj
                    elif r['crsWasChanged']:
                        tif_path_mod = new_fpath.replace('.', '_reprojected.')
                        code = r['code']
                        os.system('gdal_translate -a_srs {0} {1} {2}'.format(code, new_fpath, tif_path_mod))
                        os.remove(new_fpath)
                        os.rename(tif_path_mod, new_fpath)
                else:
                    new_fpath = os.path.join(res_contents_path, 'res_%s.vrt' % res_id)
                    os.rename(fpath, new_fpath)
                coverage_files.append(new_fpath)
            if tif_count > 1:
                return_obj['is_mosaic'] = True
            if coverage_files:
                res_fpath = os.path.join(res_contents_path, 'res_' + res_id + '.zip')
                response = make_zipfile(coverage_files, res_fpath)
                if not response['success']:
                    return_obj['message'] = response['message']
                else:
                    return_obj['is_zip'] = True
        else:
            if 'mapProject.json' in os.listdir(res_contents_path):
                res_fpath = os.path.join(res_contents_path, 'mapProject.json')
                res_type = 'GenericResource'
            else:
                for fname in os.listdir(res_contents_path):
                    fpath = os.path.join(res_contents_path, fname)

                    if fname == 'basin.kml':
                        new_fpath = os.path.join(res_contents_path, res_id + '.shp')
                        os.system('ogr2ogr -f "ESRI Shapefile" {0} {1}'.format(new_fpath, fpath))
                        res_fpath = os.path.join(res_contents_path, res_id)
                        res_type = 'GeographicFeatureResource'
                        break

                    elif fname.endswith('.tif'):
                        coverage_files = []
                        res_type = 'RasterResource'
                        r = check_crs(res_type, fpath)
                        if not r['success']:
                            return_obj['message'] = r['message']
                            return return_obj
                        elif r['crsWasChanged']:
                            tif_path_mod = fpath.replace('.', '_reprojected.')
                            code = r['code']
                            os.system('gdal_translate -a_srs {0} {1} {2}'.format(code, fpath, tif_path_mod))
                            os.remove(fpath)
                            os.rename(tif_path_mod, fpath)
                        coverage_files.append(fpath)
                        res_fpath = os.path.join(res_contents_path, 'res_' + res_id + '.zip')
                        response = make_zipfile(coverage_files, res_fpath)
                        if not response['success']:
                            return_obj['message'] = response['message']
                        else:
                            return_obj['is_zip'] = True
                        break

                    else:
                        if not os.path.exists(public_tempdir):
                            os.mkdir(public_tempdir)
                        dst = os.path.join(public_tempdir, fname)
                        os.rename(fpath, dst)
                        res_fpath = dst
                        break

        return_obj['res_filepath'] = res_fpath
        return_obj['res_type'] = res_type
        return_obj['success'] = True

    return return_obj


def get_hs_res_list(hs):
    # Deletes all stores from geoserver
    # engine = return_spatial_dataset_engine()
    # stores = engine.list_stores(get_workspace_id())
    # for store in stores['result']:
    #     engine.delete_store(store_id=store_id, purge=True, recurse=True)
    #     print "Store %s deleted" % store
    return_obj = {
        'success': False,
        'message': None,
        'res_list': None
    }
    res_list = []

    try:
        valid_res_types = ['GeographicFeatureResource', 'RasterResource', 'RefTimeSeriesResource', 'TimeSeriesResource']
        for res in hs.getResourceList(types=valid_res_types):
            res_id = res['resource_id']
            res_size = 0
            try:
                for res_file in hs.getResourceFileList(res_id):
                    res_size += res_file['size']

            except hs_r.HydroShareNotAuthorized:
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

        return_obj['res_list'] = res_list
        return_obj['success'] = True

    except hs_r.HydroShareHTTPException:
        return_obj['message'] = 'The HydroShare server appears to be down.'
    except Exception as e:
        print e
        return_obj['message'] = 'An unexpected error ocurred. App admin has been notified.'
        if gethostname() != 'ubuntu':
            email_traceback(exc_info())

    return return_obj


def get_workspace():
    global workspace_id
    if workspace_id is None:
        if 'apps.hydroshare' in gethostname():
            workspace_id = 'hydroshare_gis'
        else:
            workspace_id = 'hydroshare_gis_testing'

    return workspace_id


def email_traceback(traceback, custom_msg=None):
    exc_type, exc_value, exc_traceback = traceback
    trcbck = ''.join(format_exception(exc_type, exc_value, exc_traceback))
    msg = trcbck + custom_msg if custom_msg else trcbck
    requests.post(
        "https://api.mailgun.net/v3/sandbox5d62ce2f0725460bb5eab88b496fd2a6.mailgun.org/messages",
        auth=("api", "key-6eee015c8a719e4510a093cabf7bdfd4"),
        data={
            "from": "Mailgun Sandbox <postmaster@sandbox5d62ce2f0725460bb5eab88b496fd2a6.mailgun.org>",
            "to": "progrummer@gmail.com",
            "subject": "HydroShare GIS: Error Report",
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
        gdal_info = check_output(['gdalinfo', fpath])
        start = 'Coordinate System is:'
        length = len(start)
        end = 'Origin ='
        if gdal_info.find(start) == -1:
            return_obj['message'] = 'There is no projection information associated with this resource.' \
                                    '\nResource cannot be added to the map project.'
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
    try:
        while crs_is_unknown:
            r = requests.get(endpoint, params=params)
            response = r.json()
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
                        return_obj['crsWasChanged'] = True
                    else:
                        break
                else:
                    break
            else:
                crs_is_unknown = False
                if res_type == 'RasterResource':
                    return_obj['code'] = 'EPSG:' + response['codes'][0]['code']
                else:
                    r = requests.get(response['codes'][0]['url'])
                    proj_json = r.json()
                    raw_wkt = proj_json['wkt']
                    tmp_list = []
                    for seg in raw_wkt.split('\n'):
                        tmp_list.append(seg.strip())
                    return_obj['new_wkt'] = ''.join(tmp_list)

                return_obj['success'] = True
    except Exception as e:
        print str(e)

    return return_obj


def delete_public_tempfiles():
    if os.path.exists(public_tempdir):
        shutil.rmtree(public_tempdir)


def save_new_project(hs, project_info, res_title, res_abstract, res_keywords):
    return_obj = {
        'success': False,
        'message': None,
        'res_id': None
    }
    orig_id = None
    res_contents_path = None
    res_id = None
    try:
        res_type = 'GenericResource'
        fname = 'mapProject.json'
        tempfile = os.path.join(hs_tempdir, fname)
        project_info_json = loads(project_info)
        orig_id = project_info_json['resId']
        print orig_id

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
            # project_info['map']['resId'] = res_id
            # f.seek(0)
            # f.write(dumps(project_info_json))
            # f.truncate()
            # hs.deleteResourceFile(res_id, fname)
            # hs.addResourceFile(pid=res_id, resource_file=f, resource_filename=fname)

        project_info_json['resId'] = res_id
        with open(tempfile, 'w+') as f:
            f.write(dumps(project_info_json))

        hs.deleteResourceFile(pid=res_id, filename=fname)
        hs.addResourceFile(pid=res_id, resource_file=tempfile)

        if orig_id:
            r = download_res_from_hs(hs, orig_id)
            if not r['success']:
                return_obj['message'] = r['message']
            else:
                res_contents_path = r['res_contents_path']
                if len(os.listdir(res_contents_path)) > 1:
                    os.remove(os.path.join(res_contents_path, fname))
                    res_list = [os.path.join(res_contents_path, f) for f in os.listdir(res_contents_path)]
                    # Option 1: Add each file individually
                    for f in res_list:
                        hs.addResourceFile(pid=res_id, resource_file=f)
                    # Option 2: Add all files as a zip
                    # zip_path = os.path.join(res_contents_path, 'temp.zip')
                    # r = make_zipfile(res_list, zip_path)
                    # if not r['success']:
                    #     return_obj['message'] = r['message']
                    # else:
                    #     hs.addResourceFile(pid=res_id, resource_file=zip_path)

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
    finally:
        if orig_id and res_contents_path and os.path.exists(os.path.join(res_contents_path, orig_id)):
            shutil.rmtree(os.path.join(hs_tempdir, orig_id))

    return return_obj
