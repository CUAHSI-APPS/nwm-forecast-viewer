//Map variables
var map, base_layer, all_streams_layer, selected_streams_layer;

// NHD variables
var comid;

//Chart variables
var nc_chart, seriesData, startDate, seriesDataGroup = [];

$('#config'). on('change', function () {
    if ($('#config').val() === 'medium_range') {
        $('#endDate').addClass('hidden');
        $('#endDateLabel').addClass('hidden');
        $('#time').parent().addClass('hidden');
        $('#time').val('06')
        $('#timeLag').addClass('hidden');
    } else if ($('#config').val() === 'long_range') {
        $('#endDate').addClass('hidden');
        $('#endDateLabel').addClass('hidden');
        $('#time').parent().addClass('hidden');
        $('#time').val('00');
        $('#timeLag').removeClass('hidden');
    } else if ($('#config').val() === 'short_range') {
        $('#endDate').addClass('hidden');
        $('#endDateLabel').addClass('hidden');
        $('#time').val('00')
        $('#time').parent().removeClass('hidden');
        $('#timeLag').addClass('hidden');
    } else if ($('#config').val() === 'analysis_assim'){
        $('#endDate').removeClass('hidden');
        $('#endDateLabel').removeClass('hidden');
        $('#time').parent().addClass('hidden');
        $('#time').val('00')
        $('#timeLag').addClass('hidden');
    };
});

$(function () {
    $('[data-toggle="tooltip"]').tooltip();

    /**********************************
     **********INITIALIZE MAP *********
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

    if (window.location.search.includes('?')) {
        var query = window.location.search.split("&");

        var qLong = Number(query[2].substring(query[2].lastIndexOf("longitude=")+10));
        var qLat = Number(query[3].substring(query[3].lastIndexOf("latitude=")+9));
        var qConfig = query[0].substring(query[0].lastIndexOf("config=") + 7);
        var qCOMID = Number(query[1].substring(query[1].lastIndexOf("COMID=") + 6));
        var qDate = query[4].substring(query[4].lastIndexOf("startDate=") + 10);
        var qTime = query[5].substring(query[5].lastIndexOf("time=") + 5);
        var qLag = [];
        var qDateEnd = query[query.length - 2].substring(query[query.length - 2].lastIndexOf("endDate=") + 8);

        if (window.location.search.indexOf('00z') > -1) {
            qLag.push('00z');
        };
        if (window.location.search.indexOf('06z') > -1) {
            qLag.push('06z');
        };
        if (window.location.search.indexOf('12z') > -1) {
            qLag.push('12z');
        };
        if (window.location.search.indexOf('18z') > -1) {
            qLag.push('18z');
        };

        $('#config').val(qConfig);
        $('#comidInput').val(qCOMID);
        $('#longInput').val(qLong);
        $('#latInput').val(qLat);
        $('#startDate').val(qDate);
        $('#time').val(qTime);
        
        if ($('#longInput').val() !== '-98' && $('#latInput').val() !== '38.5') {
            CenterMap(qLat, qLong);
            map.getView().setZoom(12);

            var wktval = "POINT(" + qLong + " " + qLat + ")";
            var options = {
                "success": "pis_success2",
                "error": "pis_error",
                "timeout": 60 * 1000
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
        };

        initChart(qConfig, startDate, seriesData);

        get_netcdf_chart_data(qConfig, qCOMID, qDate, qTime, qLag, qDateEnd);
    }

    if ($('#config').val() === 'medium_range') {
        $('#endDate').addClass('hidden');
        $('#endDateLabel').addClass('hidden');
        $('#time').parent().addClass('hidden');
        $('#timeLag').addClass('hidden');
    } else if ($('#config').val() === 'long_range') {
        $('#endDate').addClass('hidden');
        $('#endDateLabel').addClass('hidden');
        $('#time').parent().addClass('hidden');
        $('#time').val('00');
        $('#timeLag').removeClass('hidden');
    }else if ($('#config').val() === 'short_range') {
        $('#endDate').addClass('hidden');
        $('#endDateLabel').addClass('hidden');
        $('#time').val('00')
        $('#time').parent().removeClass('hidden');
        $('#timeLag').addClass('hidden');
    } else if ($('#config').val() === 'analysis_assim'){
        $('#endDate').removeClass('hidden');
        $('#endDateLabel').removeClass('hidden');
        $('#time').parent().addClass('hidden');
        $('#time').val('00')
        $('#timeLag').addClass('hidden');
    };

    /**********************************
     ********INITIALIZE LAYERS*********
     **********************************/

    var lonlat;
    map.on('click', function(evt) {
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

    var srv_fl = result.output.ary_flowlines;
    var newLon = srv_fl[0].shape.coordinates[Math.floor(srv_fl[0].shape.coordinates.length/2)][0];
    var newLat = srv_fl[0].shape.coordinates[Math.floor(srv_fl[0].shape.coordinates.length/2)][1];
    comid = srv_fl[0].comid.toString();
    $('#longInput').val(newLon);
    $('#latInput').val(newLat);
    $('#comidInput').val(comid);

    //add the selected flow line to the map
    for (var i in srv_fl) {
        selected_streams_layer.getSource().clear()
        selected_streams_layer.getSource().addFeature(geojson2feature(srv_fl[i].shape));
    }
}

function pis_success2(result) {
    var srv_fl = result.output.ary_flowlines;
    var newLon = srv_fl[0].shape.coordinates[Math.floor(srv_fl[0].shape.coordinates.length/2)][0];
    var newLat = srv_fl[0].shape.coordinates[Math.floor(srv_fl[0].shape.coordinates.length/2)][1];
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

function get_netcdf_chart_data(config, comid, date, time, lag, endDate) {
    $.ajax({
        type: 'GET',
        url: 'get-netcdf-data',
        dataType: 'json',
        data: {
            'config': config,
            'comid': comid,
            'startDate': date,
            'time': time,
            'lag': lag.toString(),
            'endDate': endDate
        },
        error: function (jqXHR, textStatus, errorThrown) {
            $('#info').html('<p><strong>An unknown error occurred while retrieving the data</strong></p>');
            clearErrorSelection();
        },
        success: function (data) {
            if ("success" in data) {
                if ("ts_pairs_data" in data) {
                    var returned_tsPairsData = JSON.parse(data.ts_pairs_data);
                    for (var key in returned_tsPairsData) {
                        if (returned_tsPairsData[key].length === 2) {
                            var d = new Date(0);
                            startDate = d.setUTCSeconds(returned_tsPairsData[key][0]);
                            seriesData = returned_tsPairsData[key][1];
                            nc_chart.yAxis[0].setExtremes(null, null);
                            plotData(config, seriesData, startDate);
                        } else {
                            for (j = 0; j < returned_tsPairsData[key].length; j++) {
                                var d = new Date(0);
                                startDate = d.setUTCSeconds(returned_tsPairsData[key][j][0]);
                                for (i = 1; i < returned_tsPairsData[key][j].length - 1; i++) {
                                    var seriesDataTemp = returned_tsPairsData[key][j][i];
                                    var seriesDesc = 'Member 0' + String(i) + ' ' +
                                        returned_tsPairsData[key][j][returned_tsPairsData[key][j].length - 1];
                                    seriesDataGroup.push([seriesDataTemp, seriesDesc, startDate]);
                                    nc_chart.yAxis[0].setExtremes(null, null);
                                    plotData(config, seriesDataTemp, startDate, i - 1, seriesDesc);
                                };
                            };
                        };
                    };
                };
            } else if ("error" in data) {
                $('#nc-chart').addClass('hidden')
                $('#info').html('<p class="alert alert-danger" style="text-align: center"><strong>' + data['error'] + '</strong></p>').removeClass('hidden').addClass('error');

                // Hide error message 5 seconds after showing it
                setTimeout(function () {
                    $('#info').addClass('hidden')
                }, 5000);
            } else {
                viewer.entities.resumeEvents();
                $('#info').html('<p><strong>An unexplainable error occurred. Why? Who knows...</strong></p>').removeClass('hidden');
            };
        }
    });
};

function initChart(config, startDate) {
    /****************************
     ******INITIALIZE CHART******
     ****************************/
    if (config !== 'long_range') {
        default_chart_settings = {
            title: {text: "NWM Forecast"},
            chart: {zoomType: 'x'},
            plotOptions: {
                series: {
                    color: '#0066ff',
                    marker: {
                        enabled: false
                    }
                },
                area: {
                    fillColor: {
                        linearGradient: {x1: 0, y1: 0, x2: 0, y2: 1},
                        stops: [[0, Highcharts.getOptions().colors[0]],
                            [1, Highcharts.Color(Highcharts.getOptions().colors[0]).setOpacity(0).get('rgba')]]
                    },
                    marker: {radius: 2},
                    lineWidth: 1,
                    states: {
                        hover: {lineWidth: 1}
                    },
                    threshold: null
                }
            },
            xAxis: {
                type: 'datetime',
                title: {text: 'Time'},
                minRange: 14 * 3600000 // one day
            },
            yAxis: {
                title: {text: 'Streamflows (cfs)'},
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
                            changeUnits(config, startDate)
                        }
                    }
                }
            }
        };

        $('#nc-chart').highcharts(default_chart_settings);
        nc_chart = $('#nc-chart').highcharts();
    } else {
        default_chart_settings = {
            title: {text: "NWM Forecast"},
            chart: {zoomType: 'x'},
            plotOptions: {
                series: {
                    // color: '#0066ff',
                    marker: {
                        enabled: false
                    }
                }
            },
            xAxis: {
                type: 'datetime',
                title: {text: 'Time'},
                minRange: 14 * 3600000 // one day
            },
            yAxis: {
                title: {text: 'Streamflows (cfs)'},
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
                            changeUnits(config, startDate)
                        }
                    }
                }
            }
        };

        $('#nc-chart').highcharts(default_chart_settings);
        nc_chart = $('#nc-chart').highcharts();
    };
}

var plotData = function(config, data, startDate, colorIndex, seriesDesc) {
    $('#actionBtns').removeClass('hidden');
    var calib = calibrateModel(config, startDate)
    if (config !== 'long_range') {
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
        };
    } else {
        var data_series = {
            type: 'area',
            color: Highcharts.getOptions().colors[colorIndex],
            fillOpacity: 0.3,
            name: seriesDesc + ' Streamflow (cfs)',
            data: data,
            pointStart: calib['start'],
            pointInterval: calib['interval']
        };
        nc_chart.addSeries(data_series);
        if ($('#nc-chart').hasClass('hidden')) {
            $('#nc-chart').removeClass('hidden');
            $(window).resize();
        };
    };
};

function clearErrorSelection() {
    var numFeatures = selected_streams_layer.getSource().getFeatures().length;
    var lastFeature = selected_streams_layer.getSource().getFeatures()[numFeatures-1];
    selected_streams_layer.getSource().removeFeature(lastFeature);
}

function changeUnits(config, startDate) {
    if (config !== 'long_range') {
        if (nc_chart.yAxis[0].axisTitle.textStr === 'Streamflows (cfs)') {
            var newSeries = [];
            seriesData.forEach(function (i) {
                newSeries.push(i * 0.0283168);
            });
            var calib = calibrateModel(config, startDate)
            nc_chart.series[0].remove();
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
            nc_chart.series[0].remove();
            nc_chart.yAxis[0].setTitle({
                text: 'Streamflows (cfs)'
            });
            var data_series = {
                type: 'area',
                name: 'Streamflow (cfs)',
                data: seriesData,
                pointStart: calib['start'],
                pointInterval: calib['interval']
            };
            nc_chart.addSeries(data_series);
        };
    } else {
        if (nc_chart.yAxis[0].axisTitle.textStr === 'Streamflows (cfs)') {
            while(nc_chart.series.length > 0) {
                nc_chart.series[0].remove(true);
            }
            nc_chart.yAxis[0].setTitle({text: 'Streamflows (cms)'});

            for (i = 0; i < seriesDataGroup.length; i++) {
                var newSeries = [];
                seriesDataGroup[i][0].forEach(function (j) {
                    newSeries.push(j * 0.0283168);
                });
                var calib = calibrateModel(config, seriesDataGroup[i][2])
                var data_series = {
                    type: 'area',
                    name: seriesDataGroup[i][1] + ' Streamflow (cms)',
                    data: newSeries,
                    pointStart: calib['start'],
                    pointInterval: calib['interval']
                };
                nc_chart.addSeries(data_series);
            };
        } else {
            while(nc_chart.series.length > 0) {
                nc_chart.series[0].remove(true);
            }
            nc_chart.yAxis[0].setTitle({text: 'Streamflows (cfs)'});

            for (i = 0; i < seriesDataGroup.length; i++) {
                var calib = calibrateModel(config, seriesDataGroup[i][2])
                var data_series = {
                    type: 'area',
                    name: seriesDataGroup[i][1] + ' Streamflow (cfs)',
                    data: seriesDataGroup[i][0],
                    pointStart: calib['start'],
                    pointInterval: calib['interval']
                };
                nc_chart.addSeries(data_series);
            };
        };
    };
};

function calibrateModel(config, startDate) {
    var interval;
    var start;
    if (config === 'short_range' || config === 'analysis_assim') {
        interval = 3600 * 1000; // one hour
        start = startDate;
    } else if (config === 'medium_range') {
        interval = 3600 * 1000 * 3; // three hours
        start = startDate + (3600 * 1000 * 3); // calibrates medium range model
    } else {
        interval = 3600 * 1000 * 6; // six hours
        start = startDate;
    };
    return {'interval': interval, 'start': start}
};