from oauthlib.oauth2 import TokenExpiredError
from django.http import JsonResponse
from django.core.exceptions import ObjectDoesNotExist

from utilities import process_hs_res, get_oauth_hs, get_hs_res_list, request_wfs_info, get_geoserver_url

from json import dumps, loads
from tempfile import TemporaryFile


def add_hs_res(request):
    return_obj = {
        'success': False,
        'message': None,
        'results': {}
    }
    if request.is_ajax() and request.method == 'GET':
        if not request.GET.get('res_id'):
            return_obj['message'] = 'The required res_id parameter was not fulfilled.'
        else:
            res_id = request.GET['res_id']
            res_type = None
            res_title = None
            if request.GET.get('res_type'):
                res_type = request.GET['res_type']
            if request.GET.get('res_title'):
                res_title = request.GET['res_title']

            hs = get_oauth_hs(request)
            if hs is None:
                return_obj['message'] = 'Login timed out! Please re-sign in with your HydroShare account.'
            else:
                return_obj = process_hs_res(hs=hs, res_id=res_id, res_type=res_type, res_title=res_title)

    else:
        return_obj['message'] = 'This request can only be made through a "GET" AJAX call.'

    return JsonResponse(return_obj)


def add_local_file(request):
    """
    Controller for the "Load file from computer" button.

    :param request: the request object sent by the browser
    :returns JsonResponse: a JSON formatted response object
    """

    if request.is_ajax() and request.method == 'POST':
        pass
        # return process_local_file(request)


def ajax_get_hs_res_list(request):
    return_obj = {
        'success': False,
        'message': None,
        'res_list': None
    }

    if request.is_ajax() and request.method == 'GET':
        hs = get_oauth_hs(request)
        if hs is None:
            return_obj['message'] = 'Login timed out! Please re-sign in with your HydroShare account.'
        else:
            response = get_hs_res_list(hs)
            if not response['success']:
                return_obj['message'] = response['message']
            else:
                return_obj['res_list'] = response['res_list']
                return_obj['success'] = True
    else:
        return_obj['error'] = 'This request can only be made through a "GET" AJAX call.'

    return JsonResponse(return_obj)


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

            print 'res_title: %s' % res_title
            print 'res_abstract: %s' % res_abstract
            print 'res_keywords_raw: %s' % res_keywords_raw
            print 'res_type: %s' % res_type

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
