import logging

logger = logging.getLogger(__name__)

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

from tethys_sdk.gizmos import ToggleSwitch, DatePicker
from tethys_services.backends.hs_restclient_helper import get_oauth_hs

from .configs import *
from .subset_utilities import _get_current_utc_date


def _init_page(request):
    date_string_today, date_string_oldest, _, _ = _get_current_utc_date()

    start_date = DatePicker(name='startDate',
                            display_text='Begin Date',
                            end_date='0d',
                            autoclose=True,
                            format='yyyy-mm-dd',
                            start_date=date_string_AA_oldest,
                            today_button=True,
                            initial=date_string_today)

    end_date = DatePicker(name='endDate',
                          end_date='0d',
                          autoclose=True,
                          format='yyyy-mm-dd',
                          start_date=date_string_AA_oldest,
                          today_button=True,
                          initial=date_string_today,
                          classes="hidden")

    longRangeLag00 = ToggleSwitch(display_text='', name='00z', size='mini', initial=True)
    longRangeLag06 = ToggleSwitch(display_text='', name='06z', size='mini')
    longRangeLag12 = ToggleSwitch(display_text='', name='12z', size='mini')
    longRangeLag18 = ToggleSwitch(display_text='', name='18z', size='mini')

    hs_username = ""

    try:
        hs = get_oauth_hs(request)
        hs_username = hs.getUserInfo()['username']
        request.session['hydroshare_ready'] = True
    except Exception:
        request.session['hydroshare_ready'] = False

    waterml_url = ""

    if request.GET:
        # Make the waterml url query string
        archive =  request.GET.get("archive", "rolling")
        config = request.GET['config']
        geom = request.GET['geom']
        variable = request.GET['variable']
        if geom != 'land' and geom != 'forcing' and geom != 'terrain':
            comid = request.GET['COMID']
        else:
            comid = ','.join([request.GET['Y'], request.GET['X']])
        lon = ''
        if 'lon' in request.GET:
            lon = request.GET['lon']
        lat = ''
        if 'lat' in request.GET:
            lat = request.GET['lat']
        startDate = request.GET['startDate']

        endDate = ''
        if 'endDate' in request.GET:
            endDate = request.GET['endDate']

        time = ''
        if 'time' in request.GET:
            time = request.GET['time']

        lagList = []
        if '00z' in request.GET:
            lagList.append('t00z')
        if '06z' in request.GET:
            lagList.append('t06z')
        if '12z' in request.GET:
            lagList.append('t12z')
        if '18z' in request.GET:
            lagList.append('t18z')

        lag = ','.join(lagList)
        waterml_url = '?archive=%s&config=%s&geom=%s&variable=%s&COMID=%s&lon=%s&lat=%s&startDate=%s&endDate=%s&time=%s&lag=%s' % \
                      (archive, config, geom, variable, comid, lon, lat, startDate, endDate, time, lag)

        # watershed_obj_session = request.session.get("watershed", None)

    context = {
        'start_date': start_date,
        'end_date': end_date,
        'longRangeLag00': longRangeLag00,
        'longRangeLag06': longRangeLag06,
        'longRangeLag12': longRangeLag12,
        'longRangeLag18': longRangeLag18,
        'waterml_url': waterml_url,
        'hs_ready': request.session.get("hydroshare_ready", False),
        'hs_username': hs_username,
        # 'watershed_geojson_str': watershed_obj_session['geojson_str'] if watershed_obj_session is not None else "",
        # 'watershed_attributes_str': json.dumps(watershed_obj_session['attributes']) if watershed_obj_session is not None else "",
        "date_string_today": date_string_today,
        "date_string_oldest": date_string_oldest,
        "date_string_AA_oldest": date_string_AA_oldest,
    }
    return context


@login_required()
def home(request):
    """
    Controller for the app home page.
    """

    context = _init_page(request)
    return render(request, 'nwm_forecasts/home.html', context)


@login_required()
def subset(request):
    """
    Controller for the app home page.
    """

    context = _init_page(request)
    return render(request, 'nwm_forecasts/download.html', context)


@login_required()
def api_page(request):

    date_string_today, date_string_minus_oldest, date_string_minus_2, date_string_minus_3 = _get_current_utc_date()

    context = {
        "date_string_today": date_string_today,
        "date_string_minus_2": date_string_minus_2,
        "date_string_minus_3": date_string_minus_3,
        "date_string_minus_oldest": date_string_minus_oldest
    }
    return render(request, 'nwm_forecasts/api_page.html', context)
