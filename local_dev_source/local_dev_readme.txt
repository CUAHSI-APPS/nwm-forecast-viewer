
# this instruction applies when working with tethys_in_docker

1) Mount original nomads data ans sql DB for Subsetting page:
in docker-compose.yml_template, uncomment ## Development mode: MOUNT NWM data and subsetting query db

2) create symbolic links to nomads data for Home page:
Use subset_nwm_netcdf.create_symbolic.py

3) chown -R tethys-user:tethys-group /projects

4) ./tethys_restart