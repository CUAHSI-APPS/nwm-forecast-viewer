//variables related to the map
var map, base_layer, all_streams_layer, selected_streams_layer;
var flag_geocoded;

//variables related to the delineation process
var comid, fmeasure, gnis_name, wbd_huc12;

//variables related to the netcdf chart
var defaultChartSettings, nc_chart, plotCounter = 1, chartShowingBmks = false;

//jQuery handles
var infoDiv = $('#info');
var chartDiv =  $('#nc-chart');
var actionBtnsDiv = $('#actionBtns');

// Global data variables
var tsPairsData = {};
var rpClsData = {};
var rpBmkData = {};

$(function () {
    /**********************************
     ****INITIALIZE MAP AND LAYERS*****
     **********************************/
    map = new ol.Map({
        target: 'map-view',
        view: new ol.View({
            center: ol.proj.transform([-98, 38.5], 'EPSG:4326', 'EPSG:3857'),
            zoom: 4,
            minZoom: 2,
            maxZoom: 18
        })
    });

    var lonlat;
    map.on('click', function(evt) {
        flag_geocoded=false;
        var coordinate = evt.coordinate;
        lonlat = ol.proj.transform(coordinate, 'EPSG:3857', 'EPSG:4326');
        if (map.getView().getZoom()<12) {
            map.getView().setZoom(12);
            CenterMap(lonlat[1],lonlat[0]);
        }
        run_point_indexing_service(lonlat);
    });

    base_layer = new ol.layer.Tile({
        source: new ol.source.BingMaps({
            key: 'eLVu8tDRPeQqmBlKAjcw~82nOqZJe2EpKmqd-kQrSmg~AocUZ43djJ-hMBHQdYDyMbT-Enfsk0mtUIGws1WeDuOvjY4EXCH-9OK3edNLDgkc',
            imagerySet: 'AerialWithLabels'
        })
	});

    var createLineStyleFunction = function() {
        return function(feature, resolution) {
            var style = new ol.style.Style({
                stroke: new ol.style.Stroke({
                    color: '#ffff00',
                    width: 2
                }),
                text: new ol.style.Text({
                    textAlign: 'center',
                    textBaseline: 'middle',
                    font: 'bold 12px Verdana',
                    text: getText(feature, resolution),
                    fill: new ol.style.Fill({color: '#cc00cc'}),
                    stroke: new ol.style.Stroke({color: 'black', width: 0.5})
                })
            });
            return [style];
        };
    };

    var getText = function(feature, resolution) {
        var maxResolution = 100;
        var text = feature.get('name');
        if (resolution > maxResolution) {
            text = '';
        }
        return text;
    };

    selected_streams_layer = new ol.layer.Vector({
        source: new ol.source.Vector(),
        style: createLineStyleFunction()
    });

    var serviceUrl = 'https://watersgeo.epa.gov/arcgis/rest/services/NHDPlus_NP21/NHDSnapshot_NP21_Labeled/MapServer/0';
    var esrijsonFormat = new ol.format.EsriJSON();
    var vectorSource = new ol.source.Vector({
        loader: function(extent, resolution, projection) {
            var url = serviceUrl + '/query/?f=json&geometry=' +
                '{"xmin":' + extent[0] + ',"ymin":' + extent[1] + ',"xmax":' + extent[2] + ',"ymax":' + extent[3] +
                    ',"spatialReference":{"wkid":102100}}&inSR=102100&outSR=102100';
            $.ajax({url: url, dataType: 'jsonp', success: function(response) {
                if (response.error) {
                    alert(response.error.message + '\n' +
                        response.error.details.join('\n'));
                } else {
                // dataProjection will be read from document
                    var features = esrijsonFormat.readFeatures(response, {
                        featureProjection: projection
                    });
                    if (features.length > 0) {
                        vectorSource.addFeatures(features);
                    }
                }
            }});
        },
        strategy: ol.loadingstrategy.tile(ol.tilegrid.createXYZ({
            tileSize: 512
        }))
    });

    all_streams_layer = new ol.layer.Vector({
        source: vectorSource,
        style: new ol.style.Style({
            stroke: new ol.style.Stroke({
                color: '#0000ff',
                width: 2
            })
        }),
        maxResolution: 100
    });

    map.addLayer(base_layer);
    map.addLayer(all_streams_layer);
    map.addLayer(selected_streams_layer);

    /****************************
     ******INITIALIZE CHART******
     ****************************/
    default_chart_settings = {
        title: {text: "NWM Foracast"},
        chart: {
            zoomType: 'x'
        },
        plotOptions: {
            series: {
                color: '#0066ff',
                marker: {
                    enabled: false
                }
            },
            area: {
                fillColor: {
                    linearGradient: {
                        x1: 0,
                        y1: 0,
                        x2: 0,
                        y2: 1
                    },
                    stops: [
                        [0, Highcharts.getOptions().colors[0]],
                        [1, Highcharts.Color(Highcharts.getOptions().colors[0]).setOpacity(0).get('rgba')]
                    ]
                },
                marker: {
                    radius: 2
                },
                lineWidth: 1,
                states: {
                    hover: {
                        lineWidth: 1
                    }
                },
                threshold: null
            }
        },
        xAxis: {
            type: 'datetime',
            title: {
                text: 'Time'
            },
            minRange: 14 * 3600000 // one day
        },
        yAxis: {
            title: {
                text: 'Streamflows (cms)'
            },
            min: 0
        }
    };

    chartDiv.highcharts(default_chart_settings);
    nc_chart = chartDiv.highcharts();

    if (window.location.search.includes('?')) {
        var query = window.location.search;
        var numSeries = nc_chart.series.length;
        if (numSeries > 0) {
            nc_chart.series[numSeries - 1].remove(); //remove cms series
            plotCounter--;
        }
        var numFeatures = selected_streams_layer.getSource().getFeatures().length;
        if (numFeatures > 0) {
            var lastFeature = selected_streams_layer.getSource().getFeatures()[numFeatures - 1];
            selected_streams_layer.getSource().removeFeature(lastFeature);
        }

        var qLong = Number(query.substring(query.lastIndexOf("longitude=")+10,query.lastIndexOf("&latitude")));
        var qLat = Number(query.substring(query.lastIndexOf("latitude=")+9,query.lastIndexOf("&startDate")));
        var qConfig = query.substring(query.lastIndexOf("config=") + 7, query.lastIndexOf("&COMID"));
        var qCOMID = Number(query.substring(query.lastIndexOf("COMID=") + 6, query.lastIndexOf("&longitude")));
        var qDate = query.substring(query.lastIndexOf("startDate=") + 10, query.lastIndexOf("&time"));
        var qTime = query.substring(query.lastIndexOf("time=") + 5, query.lastIndexOf("&submit"));

        $('#comidInput').val(qCOMID);
        $('#longInput').val(qLong);
        $('#latInput').val(qLat);
        $('#startDate').val(qDate);
        $('#timeInput').val(qTime);

        var wktval = "POINT(" + qLong + " " + qLat + ")";
        var options = {
            "success" : "pis_success2",
            "error"   : "pis_error",
            "timeout" : 60 * 1000
        };
        var data = {
            "pGeometry": wktval,
            "pGeometryMod": "WKT,SRSNAME=urn:ogc:def:crs:OGC::CRS84",
            "pPointIndexingMethod": "DISTANCE",
            "pPointIndexingMaxDist": 10,
            "pOutputPathFlag": "TRUE",
            "pReturnFlowlineGeomFlag": "FULL",
            "optOutCS": "SRSNAME=urn:ogc:def:crs:OGC::CRS84",
            "optOutPrettyPrint": 0,
            "optClientRef": "CodePen"
        };
        WATERS.Services.PointIndexingService(data, options);

        CenterMap(qLat, qLong);
        map.getView().setZoom(12);

        get_netcdf_chart_data(qConfig, qCOMID, qDate, qTime);
    }
});

/****************************
 ***MAP VIEW FUNCTIONALITY***
 ****************************/

function CenterMap(lat,lon){
    var dbPoint = {
        "type": "Point",
        "coordinates": [lon, lat]
    };
    var coords = ol.proj.transform(dbPoint.coordinates, 'EPSG:4326','EPSG:3857');
    map.getView().setCenter(coords);
}

/****************************************
 *********EPA WMS FUNCTIONALITY**********
 ****************************************/

function run_point_indexing_service(lonlat) {
    var inputLon = lonlat[0];
    var inputLat = lonlat[1];
    $('#longInput').val(inputLon);
    $('#latInput').val(inputLat);
    var wktval = "POINT(" + inputLon + " " + inputLat + ")";

    var options = {
        "success" : "pis_success",
        "error"   : "pis_error",
        "timeout" : 60 * 1000
    };

    var data = {
        "pGeometry": wktval,
        "pGeometryMod": "WKT,SRSNAME=urn:ogc:def:crs:OGC::CRS84",
        "pPointIndexingMethod": "DISTANCE",
        "pPointIndexingMaxDist": 10,
        "pOutputPathFlag": "TRUE",
        "pReturnFlowlineGeomFlag": "FULL",
        "optOutCS": "SRSNAME=urn:ogc:def:crs:OGC::CRS84",
        "optOutPrettyPrint": 0,
        "optClientRef": "CodePen"
    };
    WATERS.Services.PointIndexingService(data, options);
}

function pis_success(result) {
    var srv_rez = result.output;
    if (srv_rez == null) {
        if ( result.status.status_message !== null ) {
            report_failed_search(result.status.status_message);
        } else {
            report_failed_search("No reach located near your click point.");
        }
        return;
    }

    //build output results text block for display
    var srv_fl = result.output.ary_flowlines;
    comid = srv_fl[0].comid.toString();
    $('#comidInput').val(comid);

    //add the selected flow line to the map
    for (var i in srv_fl) {
        selected_streams_layer.getSource().clear()
        selected_streams_layer.getSource().addFeature(geojson2feature(srv_fl[i].shape));
    }
}

function pis_success2(result) {
    var srv_rez = result.output;
    if (srv_rez == null) {
        if ( result.status.status_message !== null ) {
            report_failed_search(result.status.status_message);
        } else {
            report_failed_search("No reach located near your click point.");
        }
        return;
    }

    //build output results text block for display
    var srv_fl = result.output.ary_flowlines;
    comid = srv_fl[0].comid.toString();

    //add the selected flow line to the map
    for (var i in srv_fl) {
        selected_streams_layer.getSource().clear()
        selected_streams_layer.getSource().addFeature(geojson2feature(srv_fl[i].shape));
    }
}

function pis_error(XMLHttpRequest, textStatus, errorThrown) {
    report_failed_search(textStatus);
}

function report_failed_search(MessageText){
    //Set the message of the bad news
    infoDiv.append('<strong>Search Results:</strong><br>' + MessageText);
    gnis_name = null;
    map.getView().setZoom(4);
}

function geojson2feature(myGeoJSON) {
    //Convert GeoJSON object into an OpenLayers 3 feature.
    //Also force jquery coordinates into real js Array if needed
    var geojsonformatter = new ol.format.GeoJSON;
    if (myGeoJSON.coordinates instanceof Array == false) {
        myGeoJSON.coordinates = WATERS.Utilities.RepairArray(myGeoJSON.coordinates,0);
    }
    var myGeometry = geojsonformatter.readGeometry(myGeoJSON);
    myGeometry.transform('EPSG:4326','EPSG:3857');
    //name the feature according to COMID
    var newFeatureName = 'COMID: ' + comid;

    return new ol.Feature({
        geometry: myGeometry,
        name: newFeatureName
    });
}

/****************************************
 *******BUILD CHART FUNCTIONALITY********
 ****************************************/

function get_netcdf_chart_data(config, comid, startDate, time) {
    $.ajax({
        type: 'GET',
        url: 'get-netcdf-data',
        dataType: 'json',
        data: {
            'config': config,
            'comid': comid,
            'startDate': startDate,
            'time': time
        },
        error: function (jqXHR, textStatus, errorThrown) {
            infoDiv.html('<p><strong>An unknown error occurred while retrieving the data</strong></p>');
            clearErrorSelection();
        },
        success: function (data) {
            if ("success" in data) {
                if ("rp_cls_data" in data) {
                    var returned_rpClsData = JSON.parse(data.rp_cls_data);
                    for (var key in returned_rpClsData) {
                        rpClsData[key] = returned_rpClsData[key];
                    }
                }
                if ("rp_bmk_data" in data) {
                    var returned_rpBmkData = JSON.parse(data.rp_bmk_data);
                    for (var key in returned_rpBmkData) {
                        rpBmkData[key] = returned_rpBmkData[key];
                    }
                }
                if ("ts_pairs_data" in data) {
                    var returned_tsPairsData = JSON.parse(data.ts_pairs_data);
                    var actualIndexTracker = 0;
                    for (var key in returned_tsPairsData) {
                        tsPairsData[key] = returned_tsPairsData[key];
                        if (returned_tsPairsData[key][0][1] != -9999) {
                            var d = new Date(0);
                            var startDate = d.setUTCSeconds(returned_tsPairsData[key][0]);
                            var seriesData = returned_tsPairsData[key][1];
                            nc_chart.yAxis[0].setExtremes(null, null);
                            plotData(seriesData, startDate);
                        }
                        actualIndexTracker += 1
                    }
                }
            }
            else if ("error" in data) {
                chartDiv.addClass('hidden')
                infoDiv.html('<p class="alert alert-danger" style="text-align: center"><strong>' + data['error'] + '</strong></p>').removeClass('hidden').addClass('error');

                // Hide error message 5 seconds after showing it
                setTimeout(function () {
                    infoDiv.addClass('hidden')
                }, 5000);
            }
            else {
                viewer.entities.resumeEvents();
                infoDiv.html('<p><strong>An unexplainable error occurred. Why? Who knows...</strong></p>').removeClass('hidden');
            }
        }
    });
}

var plotData = function(data, startDate) {
    actionBtnsDiv.removeClass('hidden');
    var data_series = {
        type: 'area',
        name: 'Streamflow (cms)',
        data: data,
        pointStart: startDate,
        pointInterval: 3600 * 1000, // one day
    };
    nc_chart.addSeries(data_series);
    if (chartDiv.hasClass('hidden')) {
        chartDiv.removeClass('hidden');
        $(window).resize();
    }
    plotCounter++;
};

function clearErrorSelection() {
    var numFeatures = selected_streams_layer.getSource().getFeatures().length;
    var lastFeature = selected_streams_layer.getSource().getFeatures()[numFeatures-1];
    selected_streams_layer.getSource().removeFeature(lastFeature);
}