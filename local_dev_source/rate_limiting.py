
# Rate
# 1) heavy-load api: token: 60/min; anonymous: 3/min
# 2) regular api: token & anonymous: 120/min

# final_rate = rate * num_of_django_instance/worker (4 workers in our case)

import requests

# get waterml for a cell/reach
heavy_load_api = 'https://hs-apps-dev.hydroshare.org/apps/nwm-forecasts/api/GetWaterML/?config=analysis_assim&geom=land&variable=SNOWH&COMID=1635,2030&startDate=2018-04-14&endDate=2018-04-15'

# check status of a subsetting job
regular_api = "https://hs-apps-dev.hydroshare.org/apps/nwm-forecasts/api/check-subsetting-job-status/?job_id=AABBCCDD"


test_url = heavy_load_api
with_api_token = False

api_token = "aae49ba0d71d6ea25333cb8070f47f8b7fe68de3"

for i in range(500):
    r = requests.get(test_url,
                     headers={'Authorization': 'Token {0}'.format(api_token)} if with_api_token else {},
                     )
    print i, r.status_code
