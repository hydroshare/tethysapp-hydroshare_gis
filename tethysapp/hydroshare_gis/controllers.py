from django.shortcuts import render
from django.contrib.auth.decorators import login_required

from utilities import get_hs_object


@login_required()
def home(request):
    """
    Controller for the app home page.

    :param request: the request object sent by the browser
    """
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


def add_to_project(request):
    point_size_options = range(1, 31)
    stroke_width_options = range(1, 16)
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

    existing_projects = []
    resources_to_add = []

    if request.GET.get('res_ids'):
        res_ids = request.GET['res_ids'].split(',')
        hs = get_hs_object(request)

        for res_id in res_ids:
            try:
                md = hs.getSystemMetadata(res_id)
                resources_to_add.append({
                    'title': md['resource_title'],
                    'id': md['resource_id'],
                    'type': md['resource_type']
                })
            except Exception as e:
                print str(e)
                continue

        userInfo = hs.getUserInfo()
        username = userInfo['username']
        for res in hs.getResourceList(creator=username, types=['GenericResource']):
            res_id = res['resource_id']
            try:
                for res_file in hs.getResourceFileList(res_id):
                    if res_file['content_type'] == 'application/json':
                        existing_projects.append({
                            'title': res['resource_title'],
                            'id': res_id
                        })

            except Exception as e:
                print str(e)
                continue

        context['existing_projects'] = existing_projects
        context['resources_to_add'] = resources_to_add

    return render(request, 'hydroshare_gis/home.html', context)