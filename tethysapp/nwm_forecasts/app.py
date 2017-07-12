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
                    UrlMap(name='get_netcdf_data_ajax',
                           url='nwm-forecasts/get-netcdf-data',
                           controller='nwm_forecasts.controllers.get_netcdf_data'),
                    UrlMap(name='waterml',
                           url='nwm-forecasts/api/GetWaterML',
                           controller='nwm_forecasts.controllers.get_data_waterml'),
                    UrlMap(name='get_hs_watershed_list',
                           url='nwm-forecasts/get-hs-watershed-list',
                           controller='nwm_forecasts.controllers.get_hs_watershed_list'),
                    UrlMap(name='load_watershed',
                           url='nwm-forecasts/load-watershed',
                           controller='nwm_forecasts.controllers.load_watershed'),
                    UrlMap(name='subset_watershed',
                           url='nwm-forecasts/subset-watershed',
                           controller='nwm_forecasts.controllers.subset_watershed'),
                    UrlMap(name='subset_watershed_api',
                           url='nwm-forecasts/subset-watershed-api',
                           controller='nwm_forecasts.controllers.subset_watershed_api')
                    )

        return url_maps