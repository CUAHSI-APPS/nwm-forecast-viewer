//Map variables
var map, base_layer, all_streams_layer, selected_streams_layer;

// NHD variables
var comid;

//Chart variables
var nc_chart, seriesData, startDate

var hideList = ['01', '02', '03', '04', '05', '07', '08', '09', '10', '11', '13', '14', '15', '16', '17', '19', '20',
                '21', '22', '23'];

$('#config'). on('change', function () {
    if ($('#config').val() === 'medium_range') {
        $('#time').parent().addClass('hidden');
        $('#time').val('06')
    } else if ($('#config').val() === 'long_range_mem1' || $('#config').val() === 'long_range_mem2' ||
        $('#config').val() === 'long_range_mem3' || $('#config').val() === 'long_range_mem4') {
        $('#time').val('00')
        $('#time').parent().removeClass('hidden');
        for (i = 0; i < 20; i++) {
            $("#time option:contains(" + hideList[i] + ")").prop("hidden", true);
        };
    } else if ($('#config').val() === 'short_range') {
        $('#time').val('00')
        $('#time').parent().removeClass('hidden');
        for (i = 0; i < 20; i++) {
            $("#time option:contains(" + hideList[i] + ")").prop("hidden", false);
        };
    };
});

$(function () {
    $('[data-toggle="tooltip"]').tooltip();

    if ($('#config').val() === 'medium_range') {
        $('#time').parent().addClass('hidden');
    } else if ($('#config').val() === 'long_range_mem1' || $('#config').val() === 'long_range_mem2' ||
        $('#config').val() === 'long_range_mem3' || $('#config').val() === 'long_range_mem4') {
        $('#time').val('00')
        $('#time').parent().removeClass('hidden');
        for (i = 0; i < 20; i++) {
            $("#time option:contains(" + hideList[i] + ")").prop("hidden", true);
        };
    };

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
        var coordinate = evt.coordinate;
        lonlat = ol.proj.transform(coordinate, 'EPSG:3857', 'EPSG:4326');
        if (map.getView().getZoom()<12) {
            map.getView().setZoom(12);
            CenterMap(lonlat[1],lonlat[0]);
        }
        // var test = vectorSource.getClosestFeatureToCoordinate(lonlat);
        // selected_streams_layer.getSource().addFeature(test);
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
    // var serviceUrl = 'http://geoserver.byu.edu/arcgis/rest/services/NWC/NWM_Geofabric/MapServer/1';
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
        title: {text: "NWM Forecast"},
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
                text: 'Streamflows (cfs)'
            },
            min: 0
        },
        lang: {
            unitsKey: 'Switch between english and metric units'
        },
        exporting: {
            buttons: {
                customButton: {
                    text: 'Change Units',
                    _titleKey: "unitsKey",
                    onclick: function () {
                        changeUnits(qConfig, startDate, seriesData)
                    }
                }
            }
        }
    };

    $('#nc-chart').highcharts(default_chart_settings);
    nc_chart = $('#nc-chart').highcharts();

    if (window.location.search.includes('?')) {
        var query = window.location.search;

        var qLong = Number(query.substring(query.lastIndexOf("longitude=")+10,query.lastIndexOf("&latitude")));
        var qLat = Number(query.substring(query.lastIndexOf("latitude=")+9,query.lastIndexOf("&startDate")));
        var qConfig = query.substring(query.lastIndexOf("config=") + 7, query.lastIndexOf("&COMID"));
        var qCOMID = Number(query.substring(query.lastIndexOf("COMID=") + 6, query.lastIndexOf("&longitude")));
        var qDate = query.substring(query.lastIndexOf("startDate=") + 10, query.lastIndexOf("&time"));
        var qTime = query.substring(query.lastIndexOf("time=") + 5, query.lastIndexOf("&submit"));

        $('#config').val(qConfig);
        $('#comidInput').val(qCOMID);
        $('#longInput').val(qLong);
        $('#latInput').val(qLat);
        $('#startDate').val(qDate);
        $('#time').val(qTime);

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
    // console.log(srv_fl[0].shape.coordinates[0]);
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
    $('#info').append('<strong>Search Results:</strong><br>' + MessageText);
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

function get_netcdf_chart_data(config, comid, date, time) {
    $.ajax({
        type: 'GET',
        url: 'get-netcdf-data',
        dataType: 'json',
        data: {
            'config': config,
            'comid': comid,
            'startDate': date,
            'time': time
        },
        error: function (jqXHR, textStatus, errorThrown) {
            $('#info').html('<p><strong>An unknown error occurred while retrieving the data</strong></p>');
            clearErrorSelection();
        },
        success: function (data) {
            if ("success" in data) {
                if ("ts_pairs_data" in data) {
                    var returned_tsPairsData = JSON.parse(data.ts_pairs_data);
                    var actualIndexTracker = 0;
                    for (var key in returned_tsPairsData) {
                        if (returned_tsPairsData[key][0][1] != -9999) {
                            var d = new Date(0);
                            startDate = d.setUTCSeconds(returned_tsPairsData[key][0]);
                            seriesData = returned_tsPairsData[key][1];
                            nc_chart.yAxis[0].setExtremes(null, null);
                            plotData(config, seriesData, startDate);
                        }
                        actualIndexTracker += 1
                    }
                }
            }
            else if ("error" in data) {
                $('#nc-chart').addClass('hidden')
                $('#info').html('<p class="alert alert-danger" style="text-align: center"><strong>' + data['error'] + '</strong></p>').removeClass('hidden').addClass('error');

                // Hide error message 5 seconds after showing it
                setTimeout(function () {
                    $('#info').addClass('hidden')
                }, 5000);
            }
            else {
                viewer.entities.resumeEvents();
                $('#info').html('<p><strong>An unexplainable error occurred. Why? Who knows...</strong></p>').removeClass('hidden');
            }
        }
    });
}

var plotData = function(config, data, startDate) {
    $('#actionBtns').removeClass('hidden');
    var calib = calibrateModel(config, startDate)
    var data_series = {
        type: 'area',
        name: 'Streamflow (cfs)',
        data: data,
        pointStart: calib['start'],
        pointInterval: calib['interval']
    };
    nc_chart.addSeries(data_series);
    if ($('#nc-chart').hasClass('hidden')) {
        $('#nc-chart').removeClass('hidden');
        $(window).resize();
    }
};

function clearErrorSelection() {
    var numFeatures = selected_streams_layer.getSource().getFeatures().length;
    var lastFeature = selected_streams_layer.getSource().getFeatures()[numFeatures-1];
    selected_streams_layer.getSource().removeFeature(lastFeature);
}

function changeUnits(config, startDate, series) {
    if (nc_chart.yAxis[0].axisTitle.textStr === 'Streamflows (cfs)') {
        var newSeries = [];
        series.forEach(function (i) {
            newSeries.push(i * 0.0283168);
        });
        var calib = calibrateModel(config, startDate)
        nc_chart.series[0].remove()
        nc_chart.yAxis[0].setTitle({
            text: 'Streamflows (cms)'
        });
        var data_series = {
            type: 'area',
            name: 'Streamflow (cms)',
            data: newSeries,
            pointStart: calib['start'],
            pointInterval: calib['interval']
        };
        nc_chart.addSeries(data_series);
    } else {
        var calib = calibrateModel(config, startDate)
        nc_chart.series[0].remove()
        nc_chart.yAxis[0].setTitle({
            text: 'Streamflows (cfs)'
        });
        var data_series = {
            type: 'area',
            name: 'Streamflow (cfs)',
            data: series,
            pointStart: calib['start'],
            pointInterval: calib['interval']
        };
        nc_chart.addSeries(data_series);
    };
};

function calibrateModel(config, startDate) {
    var interval;
    var start;
    if (config == 'short_range') {
        interval = 3600 * 1000; // one hour
        start = startDate;
    } else if (config == 'medium_range') {
        interval = 3600 * 1000 * 3; // three hours
        start = startDate + (3600 * 1000 * 3); // calibrates medium range model
    } else {
        interval = 3600 * 1000 * 6; // six hours
        start = startDate;
    };
    return {'interval': interval, 'start': start}
};