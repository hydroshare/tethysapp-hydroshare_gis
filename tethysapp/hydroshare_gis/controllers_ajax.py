from django.http import JsonResponse

from utilities import process_hs_res, get_oauth_hs, get_hs_res_list, get_geoserver_url, delete_public_tempfiles, \
    process_local_file, save_new_project, save_project, generate_attribute_table, get_generic_files, \
    get_features_on_click


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
                return_obj = process_hs_res(hs=hs, res_id=res_id, res_type=res_type, res_title=res_title,
                                            username=request.user.username)

    else:
        return_obj['message'] = 'This request can only be made through a "GET" AJAX call.'

    return JsonResponse(return_obj)


def add_local_file(request):
    return_obj = {
        'success': False,
        'message': None,
        'results': {}
    }
    if request.is_ajax() and request.method == 'POST':
        file_list = request.FILES.getlist('files')
        proj_id = request.POST['proj_id']
        hs = get_oauth_hs(request)
        if hs is None:
            return_obj['message'] = 'Login timed out! Please re-sign in with your HydroShare account.'
        else:
            return_obj = process_local_file(file_list=file_list, proj_id=proj_id, hs=hs,
                                            username=request.user.username)
    else:
        return_obj['message'] = 'This request can only be made through a "POST" AJAX call.'

    return JsonResponse(return_obj)


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


def ajax_generate_attribute_table(request):
    if request.is_ajax() and request.method == 'GET':
        layer_id = request.GET['layerId']
        layer_attributes = request.GET['layerAttributes']

        return_obj = generate_attribute_table(layer_id, layer_attributes)
        return JsonResponse(return_obj)

def ajax_save_new_project(request):
    return_obj = {
        'success': False,
        'message': None,
        'res_id': None
    }
    if request.is_ajax() and request.method == 'GET':
        get_data = request.GET
        project_info = get_data['projectInfo']
        res_title = str(get_data['resTitle'])
        res_abstract = str(get_data['resAbstract'])
        res_keywords_raw = str(get_data['resKeywords'])
        res_keywords = res_keywords_raw.split(',')

        hs = get_oauth_hs(request)
        if hs is None:
            return_obj['message'] = 'Login timed out! Please re-sign in with your HydroShare account.'
        else:
            return_obj = save_new_project(hs=hs, project_info=project_info, res_title=res_title,
                                          res_abstract=res_abstract, res_keywords=res_keywords,
                                          username=request.user.username)

        return JsonResponse(return_obj)


def ajax_save_project(request):
    return_obj = {}

    if request.is_ajax() and request.method == 'GET':
        get_data = request.GET
        res_id = get_data['res_id']
        project_info = get_data['project_info']

        hs = get_oauth_hs(request)
        if hs is None:
            return_obj['message'] = 'Login timed out! Please re-sign in with your HydroShare account.'
        else:
            return_obj = save_project(hs, res_id, project_info)

        return JsonResponse(return_obj)


def ajax_get_geoserver_url(request):
    return get_geoserver_url(request)


def ajax_delete_public_tempfiles(request):
    if request.is_ajax and request.method == 'GET':
        delete_public_tempfiles(username=request.user.username)

    return JsonResponse({'success': True})


def ajax_get_generic_files(request):
    return_obj = {
        'success': False,
        'message': None
    }

    if request.is_ajax and request.method == 'GET':
        res_dict_string = request.GET['res_dict_string']
        hs = get_oauth_hs(request)
        if hs is None:
            return_obj['message'] = 'Login timed out! Please re-sign in with your HydroShare account.'
        else:
            return_obj = get_generic_files(hs=hs, res_dict_string=res_dict_string, username=request.user.username)

        return JsonResponse(return_obj)


def ajax_get_features_on_click(request):
    if request.is_ajax and request.method == 'GET':
        params_str = request.GET['params']
        return_obj = get_features_on_click(params_str)

        return JsonResponse(return_obj)