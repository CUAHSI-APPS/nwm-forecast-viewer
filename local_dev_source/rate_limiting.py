
# Rate
# 1) heavy-load api: token: 60/min; anonymous: 6/min
# 2) regular api: token & anonymous: 120/min

# final_rate = rate * num_of_django_instance/worker (4 workers in our case)

import requests

hs_url = "https://hs-apps-dev.hydroshare.org"
api_token = ""

#hs_url = "https://hs-apps.hydroshare.org"
#api_token = ""

#hs_url = "http://127.0.0.1:8888"
#api_token = ""


# get waterml for a cell/reach
heavy_load_api = '{}/apps/nwm-forecasts/api/GetWaterML/?config=analysis_assim&geom=land&variable=SNOWH&COMID=1635,2030&startDate=2018-03-05&endDate=2018-03-08'.format(hs_url)

# check status of a subsetting job
regular_api = "{}/apps/nwm-forecasts/api/check-subsetting-job-status/?job_id=AABBCCDD".format(hs_url)


test_url = regular_api
with_api_token = True



for i in range(500):
    r = requests.get(test_url,
                     headers={'Authorization': 'Token {0}'.format(api_token)} if with_api_token else {},
                     )
    print(i, r.status_code)
