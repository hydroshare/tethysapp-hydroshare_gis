from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

import shapefile
import cStringIO
import threading

# Global variables
total_upload_progress = 100.00
curr_upload_progress = 0.00
upload_complete = False


@login_required()
def home(request):
    """
    Controller for the app home page.

    :param request: the request object sent by the browser
    """

    context = {}

    return render(request, 'hydroshare_gis/home.html', context)


def upload_file(request):
    """
    Controller for the upload local file button.

    :param request: the request object sent by the browser
    :returns JsonResponse: a JSON formatted response containing success value and GeoJSON object if successful
    """
    global upload_complete, total_upload_progress, curr_upload_progress

    upload_complete = False

    if request.is_ajax() and request.method == 'POST':
        total_upload_progress = 100.00
        curr_upload_progress = 0.00

        t = threading.Timer(1.0, simulate_progress)
        t.start()

        # Get/check files from AJAX request
        shp_files = request.FILES.getlist('shapefiles')
        shp_file_object = None
        dbf_file_object = None
        shx_file_obejct = None
        prj_file_content = None
        filename = 'shapefile'

        for shp_file in shp_files:
            file_name = shp_file.name
            if file_name.endswith('.shp'):
                shp_file_object = cStringIO.StringIO(shp_file.read())
                filename = file_name
            elif file_name.endswith('.dbf'):
                dbf_file_object = cStringIO.StringIO(shp_file.read())
            elif file_name.endswith('.shx'):
                shx_file_obejct = cStringIO.StringIO(shp_file.read())
            elif file_name.endswith('.prj'):
                prj_file_content = shp_file.read()

        '''
        Credit: The following code was adapted from https://gist.github.com/frankrowe/6071443
        '''
        # Read the shapefile-like object
        shp_reader = shapefile.Reader(shp=shp_file_object, dbf=dbf_file_object, shx=shx_file_obejct)
        fields = shp_reader.fields[1:]
        field_names = [field[0] for field in fields]
        shp_buffer = []
        for sr in shp_reader.shapeRecords():
            atr = dict(zip(field_names, sr.record))
            geom = sr.shape.__geo_interface__
            shp_buffer.append(dict(type="Feature", geometry=geom, properties=atr))

        shp_file_object.close()
        dbf_file_object.close()

        # Write the GeoJSON object
        from json import dumps
        geojson = dumps({"type": "FeatureCollection", "features": shp_buffer}, indent=2) + "\n"
        '''
        End credit
        '''

        upload_complete = True
        return JsonResponse({
            'success': 'Files uploaded successfully.',
            'geojson': geojson,
            'projection': prj_file_content,
            'filename': filename
        })


def get_upload_progress(request):
    if request.method == 'GET':
        global total_upload_progress, curr_upload_progress
        progress = curr_upload_progress / total_upload_progress * 100
        if progress == 100:
            curr_upload_progress = 0.00
            total_upload_progress = 100.00
        return JsonResponse({
            'success': 'Files uploaded successfully.',
            'progress': progress
        })


def simulate_progress():
    global upload_complete, total_upload_progress, curr_upload_progress
    if not upload_complete and curr_upload_progress < 95:
        total_upload_progress += 1
        curr_upload_progress += 1
        t = threading.Timer(1.0, simulate_progress)
        t.start()
    else:
        while curr_upload_progress / total_upload_progress != 1:
            curr_upload_progress += 1

    return
