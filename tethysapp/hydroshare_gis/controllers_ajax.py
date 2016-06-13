from oauthlib.oauth2 import TokenExpiredError

from utilities import *

from geoserver.catalog import FailedRequestError
import shutil
from json import dumps, loads
from StringIO import StringIO
from tempfile import TemporaryFile

hs_tempdir = '/tmp/hs_gis_files/'


def load_file(request):
    """
    Controller for the "Load file from computer" button.

    :param request: the request object sent by the browser
    :returns JsonResponse: a JSON formatted response containing success value and GeoJSON object if successful
    """
    global hs_tempdir
    res_type = None
    res_title = None
    res_filepath_or_obj = None
    is_zip = False
    site_info = None
    geom_type = None
    layer_name = None
    layer_id = None
    layer_extents = None
    layer_attributes = None
    is_mosaic = False
    band_info = None

    if not os.path.exists(hs_tempdir):
        os.mkdir(hs_tempdir)

    if request.is_ajax() and request.method == 'POST':
        file_list = request.FILES.getlist('files')
        file_name = None
        for f in file_list:
            file_name = f.name
            if file_name.endswith('.shp'):
                # res_id = str(file_name[:-4].__hash__())
                res_type = 'GeographicFeatureResource'
                res_filepath_or_obj = file_list
                break
            elif file_name.endswith('.tif'):
                # res_id = str(file_name[:-4].__hash__())
                res_id = 'temp_id'
                res_type = 'RasterResource'
                res_filepath_or_obj = os.path.join(hs_tempdir, res_id, file_name[:-4] + '.zip')
                make_file_zipfile(f, file_name, res_filepath_or_obj)
                break
            elif file_name.endswith('.zip'):
                is_zip = True
                res_id = 'temp_id'
                res_zip = os.path.join(hs_tempdir, res_id, file_name)
                if not os.path.exists(res_zip):
                    if not os.path.exists(os.path.dirname(res_zip)):
                        os.mkdir(os.path.dirname(res_zip))
                with zipfile.ZipFile(res_zip, 'w', zipfile.ZIP_DEFLATED, False) as zip_object:
                    with zipfile.ZipFile(StringIO(f.read())) as z:
                        for file_name in z.namelist():
                            zip_object.writestr(file_name, z.read(file_name))
                            if file_name.endswith('.shp'):
                                res_id = str(file_name[:-4].__hash__())
                                res_type = 'GeographicFeatureResource'
                            elif file_name.endswith('.tif'):
                                res_id = str(file_name[:-4].__hash__())
                                res_type = 'RasterResource'
                os.rename(os.path.join(hs_tempdir, 'temp_id'), os.path.join(hs_tempdir, res_id))
                res_filepath_or_obj = os.path.join(hs_tempdir, res_id, file_name)

        if res_type is not None:
            hs = get_hs_object(request)
            abstract = 'This resource was created while using the HydroShare GIS App.'
            res_id = hs.createResource(
                'GenericResource',
                os.path.splitext(file_name)[0],
                resource_file=res_filepath_or_obj if res_type == 'RasterResource' else file_list,
                resource_filename=file_name,
                abstract=abstract)
        else:
            return JsonResponse({
                'error': 'Zipfile did not contain valid files.'
            })

    elif request.is_ajax() and request.method == 'GET':
        try:
            res_id = request.GET['res_id']

            hs = get_hs_object(request)
            md = hs.getSystemMetadata(res_id)

            res_type = request.GET['res_type'] if request.GET.get('res_type') else md['resource_type']
            res_title = request.GET['res_title'] if request.GET.get('res_title') else md['resource_title']
            store_id = 'res_%s' % res_id

            try:
                engine = return_spatial_dataset_engine()
                resource = engine.list_resources(store=store_id)
                if resource['success']:
                    if len(resource['result']) == 0:
                        engine.delete_store(store_id=store_id, purge=True, recurse=True)
                    else:
                        print 'RESOURCE ALREADY STORED ON GEOSERVER'
                        layer_name = resource['result'][0]
                        layer_id = '%s:%s' % (workspace_id, layer_name)
                        layer_extents, layer_attributes, geom_type = get_layer_extents_and_attributes(res_id, layer_name, res_type)
                        if res_type == 'RasterResource':
                            band_info = get_band_info(hs, res_id)

                        return JsonResponse({
                            'success': 'Files uploaded successfully.',
                            'layer_name': res_title,
                            'layer_id': layer_id,
                            'layer_extents': dumps(layer_extents),
                            'layer_attributes': layer_attributes,
                            'res_type': res_type,
                            'geom_type': geom_type,
                            'band_info': band_info
                        })
            except FailedRequestError:
                print 'RESOURCE NOT ALREADY STORED ON GEOSERVER'
            except Exception, e:
                print 'Unexpected error encountered:\n%s' % e

            print 'RESOURCE NOT ALREADY STORED ON GEOSERVER'
            if res_type == 'RefTimeSeriesResource':
                site_info = extract_site_info_from_ref_time_series(hs, res_id)
                if not site_info:
                    return get_json_response('error',
                                             'Resource not added. Required resource data not available.')
                layer_name = res_title
            else:
                hs.getResource(res_id, destination=hs_tempdir, unzip=True)
                res_contents_dir = os.path.join(hs_tempdir, res_id, res_id, 'data', 'contents')

                if os.path.exists(res_contents_dir):
                    coverage_files = []
                    for file_name in os.listdir(res_contents_dir):
                        if file_name.endswith('.shp'):
                            res_filepath_or_obj = os.path.join(res_contents_dir, file_name[:-4])
                            if res_type == 'GenericResource':
                                res_type = 'GeographicFeatureResource'
                            break
                        if file_name.endswith('.sqlite'):
                            site_info = extract_site_info_from_time_series(os.path.join(res_contents_dir, file_name))
                            layer_name = res_title
                            break
                        if file_name == 'mapProject.json':
                            res_filepath_or_obj = os.path.join(res_contents_dir, file_name)
                            break
                        if file_name.endswith('.vrt') or file_name.endswith('.tif'):
                            if file_name.endswith('.vrt'):
                                is_mosaic = True
                            coverage_files.append(os.path.join(res_contents_dir, file_name))
                            if res_type == 'GenericResource':
                                res_type = 'RasterResource'

                    if coverage_files:
                        res_filepath_or_obj = os.path.join(res_contents_dir, store_id + '.zip')
                        make_file_zipfile(coverage_files, store_id, res_filepath_or_obj)

                if res_type == 'RasterResource':
                    band_info = get_band_info(hs, res_id)

        except ObjectDoesNotExist as e:
            print str(e)
            return get_json_response('error', 'Login timed out! Please re-sign in with your HydroShare account.')
        except TokenExpiredError as e:
            print str(e)
            return get_json_response('error', 'Login timed out! Please re-sign in with your HydroShare account.')
        except Exception, e:
            print "Unexpected error encountered:"
            print str(e)
            if "401 Unauthorized" in str(e):
                return get_json_response('error', 'Username or password invalid.')
            elif "Server Error when accessing" in str(e):
                return get_json_response('error', 'This resource is currently inaccessible by HydroShare.')
            elif "was not found" in str(e):
                hs_hostname = 'www.hydroshare.org' if 'apps.hydroshare' in request.get_host() else 'playground.hydroshare.org'
                return get_json_response('error', 'This resource was not found on %s ' % hs_hostname)
            else:
                return get_json_response('error', 'An unexpected error was encountered. Resource(s) not added.')

    else:
        return get_json_response('error', 'Invalid request made.')

    if res_type == 'GenericResource':
        if res_filepath_or_obj and res_filepath_or_obj.endswith('mapProject.json'):
            with open(res_filepath_or_obj) as project_file:
                project_info = project_file.read()

            return JsonResponse({
                'success': 'Files uploaded successfully.',
                'project_info': project_info
            })
        else:
            return get_json_response('error', 'This resource does not contain content that HydroShare GIS can display.')

    if res_type == 'GeographicFeatureResource' or res_type == 'RasterResource':

        response = upload_file_to_geoserver(res_id, res_type, res_filepath_or_obj, is_zip, is_mosaic)
        if response['success']:
            layer_name = response['layer_name']
            layer_id = response['layer_id']
        else:
            return get_json_response('error', response['message'])
        layer_extents, layer_attributes, geom_type = get_layer_extents_and_attributes(res_id, layer_name, res_type)

        if layer_name and 'res_' in layer_name:
            layer_name = res_title

    if res_id:
        if os.path.exists(os.path.join(hs_tempdir, res_id)):
            print "DELETING THE TEMP DIRECTORY"
            shutil.rmtree(os.path.join(hs_tempdir, res_id))

    return JsonResponse({
        'success': 'Files uploaded successfully.',
        'layer_name': layer_name,
        'layer_id': layer_id,
        'layer_extents': layer_extents,
        'layer_attributes': layer_attributes,
        'res_type': res_type,
        'site_info': site_info,
        'res_id': res_id,
        'geom_type': geom_type,
        'band_info': band_info
    })


def get_hs_res_list(request):
    if request.is_ajax() and request.method == 'GET':
        # print "DELETEING ALL STORES FROM GEOSERVER"
        # engine = return_spatial_dataset_engine()
        # stores = engine.list_stores(workspace_id)
        # for store in stores['result']:
        #     engine.delete_store(store, True, True)
        #     print "Store %s deleted" % store

        resources_list = []

        hs = get_hs_object(request)

        types = ['GeographicFeatureResource', 'RasterResource', 'RefTimeSeriesResource', 'TimeSeriesResource']

        for resource in hs.getResourceList(types=types):

            res_id = resource['resource_id']
            res_size = 0

            try:
                for res_file in hs.getResourceFileList(res_id):
                    res_size += res_file['size']

            except Exception as e:
                print str(e)
                continue

            resources_list.append({
                'title': resource['resource_title'],
                'type': resource['resource_type'],
                'id': res_id,
                'size': sizeof_fmt(res_size) if res_size != 0 else "N/A",
                'owner': resource['creator']
            })

        resources_json = dumps(resources_list)

        return JsonResponse({
            'success': 'Resources obtained successfully.',
            'resources': resources_json
        })


def generate_attribute_table(request):
    if request.is_ajax() and request.method == 'GET':
        layer_id = request.GET['layerId']
        layer_attributes = request.GET['layerAttributes']

        params = {
            'service': 'wfs',
            'version': '2.0.0',
            'request': 'GetFeature',
            'typeNames': layer_id,
            'propertyName': layer_attributes,
            'outputFormat': 'application/json'
        }

        r = request_wfs_info(params)
        json = r.json()

        feature_properties = []

        features = json['features']
        for feature in features:
            feature_properties.append(feature['properties'])

        return JsonResponse({
            'success': 'Resources obtained successfully.',
            'feature_properties': dumps(feature_properties)
        })

def save_new_project(request):
    return_json = {}
    fname = 'mapProject.json'

    if request.is_ajax() and request.method == 'GET':
        try:
            get_data = request.GET
            project_info = loads(get_data['projectInfo'])
            res_title = str(get_data['resTitle'])
            res_abstract = str(get_data['resAbstract'])
            res_keywords_raw = str(get_data['resKeywords'])
            res_keywords = res_keywords_raw.split(',')
            res_type = 'GenericResource'

            hs = get_oauth_hs(request)
            with TemporaryFile() as f:
                f.write(dumps(project_info))
                f.seek(0)
                res_id = hs.createResource(res_type,
                                           res_title,
                                           resource_file=f,
                                           resource_filename=fname,
                                           keywords=res_keywords,
                                           abstract=res_abstract
                                           )

            return_json['success'] = 'Resource created successfully.'
            return_json['res_id'] = res_id

        except (ObjectDoesNotExist, TokenExpiredError) as e:
            print str(e)
            return_json['error'] = 'Login timed out! Please re-sign in with your HydroShare account.'
        except Exception as e:
            print str(e)
            return_json['error'] = 'An unknown/unexpected error was encountered. Project not saved.'

        return JsonResponse(return_json)


def save_project(request):
    return_json = {}
    fname = 'mapProject.json'

    if request.is_ajax() and request.method == 'GET':
        try:
            get_data = request.GET
            res_id = get_data['res_id']
            project_info = loads(get_data['project_info'])

            hs = get_oauth_hs(request)
            res_id = hs.deleteResourceFile(res_id, fname)

            with TemporaryFile() as f:
                f.write(dumps(project_info))
                f.seek(0)
                hs.addResourceFile(res_id, f, fname)
            return_json['success'] = 'Resource saved successfully.'

        except (ObjectDoesNotExist, TokenExpiredError) as e:
            print str(e)
            return_json['error'] = 'Login timed out! Please re-sign in with your HydroShare account.'
        except Exception as e:
            print str(e)
            return_json['error'] = 'An unknown/unexpected error was encountered. Project not saved.'

        return JsonResponse(return_json)


def ajax_get_geoserver_url(request):
    return get_geoserver_url(request)
