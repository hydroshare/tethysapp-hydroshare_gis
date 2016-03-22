from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from oauthlib.oauth2 import TokenExpiredError
from utilities import *
from geoserver.catalog import FailedRequestError

import shutil
from json import dumps, loads
from StringIO import StringIO

hs_tempdir = '/tmp/hs_gis_files/'
project_file_tempdir = '/tmp/hs_proj_files'


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

    context = {
        'point_size_options': point_size_options,
        'stroke_width_options': stroke_width_options,
        'point_shape_options': point_shape_options,
        'font_size_options': font_size_options
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

            # hs = get_oauth_hs(request)
            hs = HydroShare()

            print 'GET REQUEST MADE'
            res_id = request.GET['res_id']
            print 'res_id: %s' % res_id

            if 'res_type' in request.GET:
                res_type = request.GET['res_type']
            else:
                res_type = hs.getSystemMetadata(res_id)['resource_type']
            print 'res_type: %s' % res_type
            if 'res_title' in request.GET:
                res_title = request.GET['res_title']
            else:
                res_title = hs.getSystemMetadata(res_id)['resource_title']
            print 'res_title: %s' % res_title
            store_id = 'res_%s' % res_id
            print 'store_id: %s' % store_id
            try:
                if engine.list_resources(store=store_id)['success']:
                    print 'RESOURCE ALREADY STORED ON GEOSERVER'
                    # RESOURCE ALREADY STORED ON GEOSERVER
                    layer_name = engine.list_resources(store=store_id)['result'][0]
                    print 'layer_name: %s' % layer_name
                    layer_id = '%s:%s' % (workspace_id, layer_name)
                    print 'layer_id: %s' % layer_id
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
                print e
                pass
            except Exception, e:
                print e

            # RESOURCE NOT ALREADY STORED ON GEOSERVER
            hs.getResource(res_id, destination=hs_tempdir, unzip=True)
            res_contents_dir = os.path.join(hs_tempdir, res_id, res_id, 'data', 'contents')
            print 'res_contents_dir: %s' % res_contents_dir

            if os.path.exists(res_contents_dir):
                print "res_contents_dir exists"
                for file_name in os.listdir(res_contents_dir):
                    print "file_name: %s" % file_name
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

            print 'res_filepath_or_obj: %s' % res_filepath_or_obj

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

    if res_type != 'TimeSeriesResource':
        layer_name, layer_id = upload_file_to_geoserver(res_id, res_type, res_filepath_or_obj, is_zip)
        print 'layer_id: %s' % layer_id

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
        valid_res_list = []

        # hs = get_oauth_hs(request)
        hs = HydroShare()

        for resource in hs.getResourceList(
                types=['GeographicFeatureResource', 'RasterResource', 'RefTimeSeriesResource', 'TimeSeriesResource']):

            res_id = resource['resource_id']
            res_size = 0

            try:
                for res_file in hs.getResourceFileList(res_id):
                    res_size += res_file['size']

            except Exception, err:
                print str(err)
                continue  # Can be removed if public not being public error is fixed

            valid_res_list.append({
                'title': resource['resource_title'],
                'type': resource['resource_type'],
                'id': res_id,
                'size': sizeof_fmt(res_size) if res_size != 0 else "N/A",
                'owner': resource['creator']
            })

        valid_res_json = dumps(valid_res_list)

        return JsonResponse({
            'success': 'Resources obtained successfully.',
            'resources': valid_res_json
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
    if request.is_ajax() and request.method == 'GET':
        map_project = loads(request.GET['projectInfo'])


        if not os.path.exists(project_file_tempdir):
            os.mkdir(project_file_tempdir)

        proj_file = os.path.join(project_file_tempdir, 'currentProject')
        with open(proj_file, 'w+') as proj_file_reader:
            proj_file_reader.write(dumps(map_project))

        return JsonResponse({
            'success': 'Resources created successfully.',
            'res_id': '###res_id to go here####'
        })
