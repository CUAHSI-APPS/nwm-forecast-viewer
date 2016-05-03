from tethys_sdk.base import TethysAppBase, url_map_maker


class WrfHydroForecasts(TethysAppBase):
    """
    Tethys app class for WRF Hydro Forecasts.
    """

    name = 'National Water Model Forecast Viewer'
    index = 'wrf_hydro_forecasts:home'
    icon = 'wrf_hydro_forecasts/images/icon.gif'
    package = 'wrf_hydro_forecasts'
    root_url = 'wrf-hydro-forecasts'
    color = '#e74c3c'
    description= 'This app allows the user to visualize National Water Model forecasts for a specific NHD stream reach.'
    enable_feedback = False
    feedback_emails = []

        
    def url_maps(self):
        """
        Add controllers
        """
        UrlMap = url_map_maker(self.root_url)

        url_maps = (UrlMap(name='home',
                           url='wrf-hydro-forecasts',
                           controller='wrf_hydro_forecasts.controllers.home'),
                    UrlMap(name='get_netcdf_data_ajax',
                           url='wrf-hydro-forecasts/get-netcdf-data',
                           controller='wrf_hydro_forecasts.controllers.get_netcdf_data'),
                    UrlMap(name='start_file_download_ajax',
                           url='wrf-hydro-forecasts/start-file-download',
                           controller='wrf_hydro_forecasts.controllers.start_file_download'),
                    # UrlMap(name='delete_file_ajax',
                    #        url='wrf-hydro-forecasts/delete-file',
                    #        controller='wrf_hydro_forecasts.controllers.delete_file')
                    )

        return url_maps