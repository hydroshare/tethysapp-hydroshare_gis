from tethys_sdk.base import TethysAppBase, url_map_maker


class HydroshareGis(TethysAppBase):
    """
    Tethys app class for HydroShare GIS.
    """

    name = 'HydroShare GIS'
    index = 'hydroshare_gis:home'
    icon = 'hydroshare_gis/images/icon.gif'
    package = 'hydroshare_gis'
    root_url = 'hydroshare-gis'
    color = '#1abc9c'
    description = 'View Raster and Feature Resources from HydroShare or uploaded from ' \
                  'your own computer.'
    enable_feedback = True
    feedback_emails = ['scrawley@byu.edu']

    def url_maps(self):
        """
        Add controllers
        """
        url_map = url_map_maker(self.root_url)

        url_maps = (url_map(name='home',
                            url='hydroshare-gis',
                            controller='hydroshare_gis.controllers.home'),
                    url_map(name='add_to_project',
                            url='hydroshare-gis/add-to-project',
                            controller='hydroshare_gis.controllers.home'),
                    url_map(name='add_local_file',
                            url='hydroshare-gis/add-local-file',
                            controller='hydroshare_gis.controllers_ajax.add_local_file'),
                    url_map(name='add_hs_res',
                            url='hydroshare-gis/add-hs-res',
                            controller='hydroshare_gis.controllers_ajax.add_hs_res'),
                    url_map(name='get_hs_res_list',
                            url='hydroshare-gis/get-hs-res-list',
                            controller='hydroshare_gis.controllers_ajax.ajax_get_hs_res_list'),
                    url_map(name='ajax_generate_attribute_table',
                            url='hydroshare-gis/generate-attribute-table',
                            controller='hydroshare_gis.controllers_ajax.ajax_generate_attribute_table'),
                    url_map(name='ajax_save_new_project',
                            url='hydroshare-gis/save-new-project',
                            controller='hydroshare_gis.controllers_ajax.ajax_save_new_project'),
                    url_map(name='ajax_save_project',
                            url='hydroshare-gis/save-project',
                            controller='hydroshare_gis.controllers_ajax.ajax_save_project'),
                    url_map(name='ajax_get_geoserver_url',
                            url='hydroshare-gis/get-geoserver-url',
                            controller='hydroshare_gis.controllers_ajax.ajax_get_geoserver_url'),
                    url_map(name='ajax_delete_public_tempfiles',
                            url='hydroshare-gis/delete-public-tempfiles',
                            controller='hydroshare_gis.controllers_ajax.ajax_delete_public_tempfiles')
                    )
        return url_maps
