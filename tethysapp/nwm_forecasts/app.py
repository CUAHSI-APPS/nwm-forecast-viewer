from tethys_sdk.base import TethysAppBase, url_map_maker


class nwmForecasts(TethysAppBase):
    """
    Tethys app class for WRF Hydro Forecasts.
    """

    name = 'National Water Model Forecast Viewer'
    index = 'nwm_forecasts:home'
    icon = 'nwm_forecasts/images/nwm_forecasts.png'
    package = 'nwm_forecasts'
    root_url = 'nwm-forecasts'
    color = '#e74c3c'
    description = 'This app allows the user to visualize National Water Model forecasts.'
    enable_feedback = False
    feedback_emails = []

    def url_maps(self):
        """
        Add controllers
        """
        UrlMap = url_map_maker(self.root_url)

        url_maps = (UrlMap(name='home',
                           url='nwm-forecasts',
                           controller='nwm_forecasts.controllers.home'),
                    UrlMap(name='subset',
                           url='nwm-forecasts/subset',
                           controller='nwm_forecasts.controllers.subset'),
                    UrlMap(name='api_page',
                           url='nwm-forecasts/api-page',
                           controller='nwm_forecasts.controllers.api_page'),
                    # ajax
                    UrlMap(name='subset_watershed',
                           url='nwm-forecasts/subset-watershed',
                           controller='nwm_forecasts.controllers_ajax.subset_watershed'),
                    UrlMap(name='get_netcdf_data_ajax',
                           url='nwm-forecasts/get-netcdf-data',
                           controller='nwm_forecasts.controllers_ajax.get_netcdf_data'),
                    UrlMap(name='get_hs_watershed_list',
                           url='nwm-forecasts/get-hs-watershed-list',
                           controller='nwm_forecasts.controllers_ajax.get_hs_watershed_list'),
                    UrlMap(name='load_watershed',
                           url='nwm-forecasts/load-watershed',
                           controller='nwm_forecasts.controllers_ajax.load_watershed'),
                    # API
                    UrlMap(name='waterml',
                           url='nwm-forecasts/api/GetWaterML',
                           controller='nwm_forecasts.apis.get_data_waterml'),
                    UrlMap(name='submit_subsetting_job',
                           url='nwm-forecasts/api/submit-subsetting-job',
                           controller='nwm_forecasts.apis.subset_watershed_api'),
                    UrlMap(name='check_subsetting_job_status',
                           url='nwm-forecasts/api/check-subsetting-job-status',
                           controller='nwm_forecasts.apis.check_subsetting_job_status'),
                    UrlMap(name='download_subsetting_results',
                           url='nwm-forecasts/api/download-subsetting-results',
                           controller='nwm_forecasts.apis.download_subsetting_results'),
                    UrlMap(name='spatial_query_api',
                           url='nwm-forecasts/api/spatial-query',
                           controller='nwm_forecasts.apis.spatial_query_api'),
                    UrlMap(name='check_latest_data',
                           url='nwm-forecasts/api/latest-data-info',
                           controller='nwm_forecasts.apis.check_latest_data_api'),
                    )

        return url_maps
