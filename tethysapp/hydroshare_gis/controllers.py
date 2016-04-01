from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from oauthlib.oauth2 import TokenExpiredError
from utilities import *
from geoserver.catalog import FailedRequestError
from django.core.exceptions import ObjectDoesNotExist

import shutil
from json import dumps, loads
from StringIO import StringIO

hs_tempdir = '/tmp/hs_gis_files/'
project_file_tempdir = '/tmp/hs_proj_files'
engine = None

@login_required()
def home(request):
    """
    Controller for the app home page.

    :param request: the request object sent by the browser
    """
    global engine

    engine = return_spatial_dataset_engine()

    point_size_options = range(1, 31)
    stroke_width_options = range(1,16)
    point_shape_options = ['circle', 'square', 'triangle', 'star', 'cross', 'X']
    font_size_options = range(8, 37, 2)
    num_gradient_colors_options = range(2, 9)

    context = {
        'point_size_options': point_size_options,
        'stroke_width_options': stroke_width_options,
        'point_shape_options': point_shape_options,
        'font_size_options': font_size_options,
        'num_gradient_colors_options': num_gradient_colors_options
    }

    return render(request, 'hydroshare_gis/home.html', context)


def load_file(request):
    """
    Controller for the "Load file from computer" button.

    :param request: the request object sent by the browser
    :returns JsonResponse: a JSON formatted response containing success value and GeoJSON object if successful
    """
    global hs_tempdir, engine
    res_id = None
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

    if not os.path.exists(hs_tempdir):
        os.mkdir(hs_tempdir)

    if request.is_ajax() and request.method == 'POST':
        res_files = request.FILES.getlist('files')

        for res_file in res_files:
            file_name = res_file.name
            if file_name.endswith('.shp'):
                res_id = str(file_name[:-4].__hash__())
                res_type = 'GeographicFeatureResource'
                res_filepath_or_obj = res_files
                break
            elif file_name.endswith('.tif'):
                res_id = str(file_name[:-4].__hash__())
                res_type = 'RasterResource'
                res_zip = os.path.join(hs_tempdir, res_id, file_name[:-4] + '.zip')
                make_file_zipfile(res_file, file_name, res_zip)
                res_filepath_or_obj = res_zip
                break
            elif file_name.endswith('.zip'):
                is_zip = True
                res_id = 'temp_id'
                res_zip = os.path.join(hs_tempdir, res_id, file_name)
                if not os.path.exists(res_zip):
                    if not os.path.exists(os.path.dirname(res_zip)):
                        os.mkdir(os.path.dirname(res_zip))
                with zipfile.ZipFile(res_zip, 'w', zipfile.ZIP_DEFLATED, False) as zip_object:
                    with zipfile.ZipFile(StringIO(res_file.read())) as z:
                        for name in z.namelist():
                            zip_object.writestr(name, z.read(name))
                            if name.endswith('.shp'):
                                res_id = str(name[:-4].__hash__())
                                res_type = 'GeographicFeatureResource'
                            elif name.endswith('.tif'):
                                res_id = str(name[:-4].__hash__())
                                res_type = 'RasterResource'
                os.rename(os.path.join(hs_tempdir, 'temp_id'), os.path.join(hs_tempdir, res_id))
                res_filepath_or_obj = os.path.join(hs_tempdir, res_id, file_name)

    elif request.is_ajax() and request.method == 'GET':
        try:
            # CLEAR ALL OF THE GEOSERVER RESOURCES
            # stores = engine.list_stores(workspace_id)
            # for store in stores['result']:
            #     engine.delete_store(store, True, True)

            try:
                hs = get_oauth_hs(request)
            except ObjectDoesNotExist as e:
                print str(e)
                hs = HydroShare()

            res_id = request.GET['res_id']

            if 'res_type' in request.GET:
                res_type = request.GET['res_type']
            else:
                res_type = hs.getSystemMetadata(res_id)['resource_type']

            if 'res_title' in request.GET:
                res_title = request.GET['res_title']
            else:
                res_title = hs.getSystemMetadata(res_id)['resource_title']

            store_id = 'res_%s' % res_id

            try:
                if engine.list_resources(store=store_id)['success']:
                    # RESOURCE ALREADY STORED ON GEOSERVER
                    layer_name = engine.list_resources(store=store_id)['result'][0]
                    layer_id = '%s:%s' % (workspace_id, layer_name)
                    layer_extents, layer_attributes, geom_type = get_layer_extents_and_attributes(res_id, layer_name, res_type)

                    return JsonResponse({
                        'success': 'Files uploaded successfully.',
                        'geoserver_url': geoserver_url,
                        'layer_name': res_title,
                        'layer_id': layer_id,
                        'layer_extents': dumps(layer_extents),
                        'layer_attributes': layer_attributes,
                        'res_type': res_type,
                        'geom_type': geom_type
                    })
            except FailedRequestError, e:
                print str(e)
            except Exception, e:
                print str(e)

            # RESOURCE NOT ALREADY STORED ON GEOSERVER
            hs.getResource(res_id, destination=hs_tempdir, unzip=True)
            res_contents_dir = os.path.join(hs_tempdir, res_id, res_id, 'data', 'contents')

            if os.path.exists(res_contents_dir):
                for file_name in os.listdir(res_contents_dir):
                    if file_name.endswith('.shp'):
                        res_filepath_or_obj = os.path.join(res_contents_dir, file_name[:-4])
                        break
                    elif file_name.endswith('.tif'):
                        res_filepath_or_obj = os.path.join(res_contents_dir, file_name[:-4] + '.zip')
                        make_file_zipfile(os.path.join(res_contents_dir, file_name), file_name, res_filepath_or_obj)
                        break
                    elif file_name.endswith('.sqlite'):
                        site_info = extract_site_info_from_time_series(os.path.join(res_contents_dir, file_name))
                        layer_name = res_title
                    elif file_name.endswith('.json'):
                        res_filepath_or_obj = os.path.join(res_contents_dir, file_name)

        except ObjectDoesNotExist as e:
            print str(e)
            return get_json_response('error', 'Login timed out! Please re-sign in with your HydroShare account.')
        except TokenExpiredError as e:
            print str(e)
            return get_json_response('error', 'Login timed out! Please re-sign in with your HydroShare account.')
        except Exception, e:
            print str(e)
            if "401 Unauthorized" in str(e):
                return get_json_response('error', 'Username or password invalid.')

    else:
        return get_json_response('error', 'Invalid request made.')

    if res_type == 'GenericResource' and res_filepath_or_obj.endswith('.json'):
        with open(res_filepath_or_obj) as project_file:
            project_info = project_file.read()

        return JsonResponse({
            'success': 'Files uploaded successfully.',
            'project_info': project_info
        })

    if res_type == 'GeographicFeatureResource' or res_type == 'RasterResource':
        layer_name, layer_id = upload_file_to_geoserver(res_id, res_type, res_filepath_or_obj, is_zip)
        layer_extents, layer_attributes, geom_type = get_layer_extents_and_attributes(res_id, layer_name, res_type)

        if layer_name and 'res_' in layer_name:
            layer_name = res_title

    if res_id:
        if os.path.exists(os.path.join(hs_tempdir, res_id)):
            shutil.rmtree(os.path.join(hs_tempdir, res_id))

    return JsonResponse({
        'success': 'Files uploaded successfully.',
        'geoserver_url': geoserver_url,
        'layer_name': layer_name,
        'layer_id': layer_id,
        'layer_extents': layer_extents,
        'layer_attributes': layer_attributes,
        'res_type': res_type,
        'site_info': site_info,
        'res_id': res_id,
        'geom_type': geom_type
    })


def get_hs_res_list(request):
    if request.is_ajax() and request.method == 'GET':
        resources_list = []

        try:
            hs = get_oauth_hs(request)
        except ObjectDoesNotExist as e:
            print str(e)
            hs = HydroShare()

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

def save_project(request):
    global project_file_tempdir
    return_json = {}

    if request.is_ajax() and request.method == 'GET':
        try:
            get_data = request.GET
            project_info = loads(get_data['projectInfo'])
            res_title = str(get_data['resTitle'])
            res_abstract = str(get_data['resAbstract'])
            res_keywords_raw = str(get_data['resKeywords'])
            res_keywords = res_keywords_raw.split(',')
            res_type = 'GenericResource'

            if not os.path.exists(project_file_tempdir):
                os.mkdir(project_file_tempdir)

            proj_file = os.path.join(project_file_tempdir, 'mapProject.json')
            with open(proj_file, 'w+') as proj_file_reader:
                proj_file_reader.write(dumps(project_info))

            hs = get_oauth_hs(request)

            # upload the temp file to HydroShare
            if os.path.exists(proj_file):
                res_id = hs.createResource(res_type,
                                           res_title,
                                           resource_file=proj_file,
                                           keywords=res_keywords,
                                           abstract=res_abstract
                                           )

                return_json['success'] = 'Resources created successfully.'
                return_json['res_id'] = res_id

        except ObjectDoesNotExist as e:
            print str(e)
            return_json['error'] = 'Login timed out! Please re-sign in with your HydroShare account.'

        except TokenExpiredError as e:
            print str(e)
            return_json['error'] = 'Login timed out! Please re-sign in with your HydroShare account.'
        except Exception as e:
            if "401 Unauthorized" in str(e):
                return_json['error'] = 'Username or password invalid.'
            elif "400 Bad Request" in str(e):
                return_json['success'] = 'File uploaded successfully despite 400 Bad Request Error.'
            else:
                return_json['error'] = 'HydroShare rejected the upload for some reason.'
        finally:
            if os.path.exists(project_file_tempdir):
                shutil.rmtree(project_file_tempdir)

            return JsonResponse(return_json)