//Map variables
var map, mapView, base_layer, all_streams_layer, selected_streams_layer;

// NHD variables
var comid;

//Chart variables
var nc_chart, seriesData, startDate, seriesDataGroup = [];

//jQuery handle variables
var $btnLoadWatershed;
var $popupLoadWatershed;

$('#config').on('change', function () {
    if ($('#config').val() === 'medium_range') {
        $('#endDate,#endDateLabel,#timeLag').addClass('hidden');
        $('#time').parent().addClass('hidden');
        if ($('#geom').val() === 'channel_rt' && $('#config').val() !== 'long_range') {
            $('#velocVar').removeClass('hidden');
        };
        $('#time').val('06')
    } else if ($('#config').val() === 'long_range') {
        $('#endDate,endDateLabel,#velocVar').addClass('hidden');
        $('#time').parent().addClass('hidden');
        $('#timeLag').removeClass('hidden');
    } else if ($('#config').val() === 'short_range') {
        $('#endDate,#endDateLabel,#timeLag').addClass('hidden');
        $('#time').parent().removeClass('hidden');
        if ($('#geom').val() === 'channel_rt' && $('#config').val() !== 'long_range') {
            $('#velocVar').removeClass('hidden');
        };
    } else if ($('#config').val() === 'analysis_assim'){
        $('#endDate,#endDateLabel').removeClass('hidden');
        $('#time').parent().addClass('hidden');
        $('#timeLag').addClass('hidden');
        if ($('#geom').val() === 'channel_rt' && $('#config').val() !== 'long_range') {
            $('#velocVar').removeClass('hidden');
        };
    }
    $("#geom").trigger("change");
});


$('#geom').on('change', function () {
    if ($('#geom').val() === 'channel_rt') {
        $('#comidInput').attr('disabled', false);
        if (window.location.search.includes('channel_rt') && window.location.search.includes('long_range') === false) {
            $('#variable').val(window.location.search.split("&")[2].substring(window.location.search.split("&")[2].
                lastIndexOf("variable=") + 9));
        } else {
            $('#variable').val('streamflow');
        };
        $('#comidDiv,#streamVar').removeClass('hidden');
        if ($('#config').val() !== 'long_range') {
            $('#velocVar').removeClass('hidden');
        }
        $('#gridInputY').attr('disabled', true);
        $('#gridInputX').attr('disabled', true);
        $('#gridDiv,#infVar,#outfVar,#snowhVar,#sneqVar,#snowcVar,#etVar,#ssVar,#avsnowVar,#subrunoffVar,#runoffVar,#canwVar,#ssiVar,#evapVar,#soiltVar,#soilmVar').
            addClass('hidden');
    } else if ($('#geom').val() === 'reservoir') {
        $('#comidInput').attr('disabled', false);
        if (window.location.search.includes('reservoir')) {
            $('#variable').val(window.location.search.split("&")[2].substring(window.location.search.split("&")[2].
                lastIndexOf("variable=") + 9));
        } else {
            $('#variable').val('inflow');
        };
        $('#comidDiv,#infVar,#outfVar').removeClass('hidden');
        $('#gridInputY').attr('disabled', true);
        $('#gridInputX').attr('disabled', true);
        $('#gridDiv,#streamVar,#velocVar,#snowhVar,#sneqVar,#snowcVar,#etVar,#ssVar,#avsnowVar,#subrunoffVar,#runoffVar,#canwVar,#ssiVar,#evapVar,#soiltVar,#soilmVar').
            addClass('hidden');
    } else if ($('#geom').val() === 'land' && ($('#config').val() === 'short_range' ||
        $('#config').val() === 'analysis_assim')) {
        $('#comidInput').attr('disabled', true);
        $('#comidDiv,#streamVar,#velocVar,#infVar,#outfVar,#subrunoffVar,#runoffVar,#evapVar,#soiltVar,#soilmVar,#canwVar,#ssiVar')
            .addClass('hidden');
        $('#gridInputY').attr('disabled', false);
        $('#gridInputX').attr('disabled', false);
        if (window.location.search.includes('land')) {
            $('#variable').val(window.location.search.split("&")[2].substring(window.location.search.split("&")[2].
                lastIndexOf("variable=") + 9));
        } else {
            $('#variable').val('SNOWH');
        };
        $('#gridDiv,#snowhVar,#sneqVar,#snowcVar,#etVar,#ssVar,#avsnowVar').removeClass('hidden');
    } else if ($('#geom').val() === 'land' && $('#config').val() === 'medium_range') {
        $('#comidInput').attr('disabled', true);
        $('#comidDiv,#streamVar,#velocVar,#infVar,#outfVar,#runoffVar,#ssiVar').
            addClass('hidden');
        $('#gridInputY').attr('disabled', false);
        $('#gridInputX').attr('disabled', false);
        if (window.location.search.includes('land')) {
            $('#variable').val(window.location.search.split("&")[2].substring(window.location.search.split("&")[2].
                lastIndexOf("variable=") + 9));
        } else {
            $('#variable').val('SNOWH');
        };
        $('#gridDiv,#snowhVar,#sneqVar,#snowcVar,#etVar,#ssVar,#avsnowVar,#subrunoffVar,#evapVar,#canwVar,#soiltVar,#soilmVar').
            removeClass('hidden');
    } else if ($('#geom').val() === 'land' && $('#config').val() === 'long_range') {
        $('#comidInput').attr('disabled', true);
        $('#comidDiv,#streamVar,#velocVar,#infVar,#outfVar,#snowhVar,#snowcVar,#avsnowVar,#evapVar,#soiltVar,#soilmVar')
            .addClass('hidden');
        $('#gridInputY').attr('disabled', false);
        $('#gridInputX').attr('disabled', false);
        if (window.location.search.includes('land') && window.location.search.includes('long_range')) {
            $('#variable').val(window.location.search.split("&")[2].substring(window.location.search.split("&")[2].
                lastIndexOf("variable=") + 9));
        } else {
            $('#variable').val('SNEQV');
        };
        $('#gridDiv,#sneqVar,#etVar,#ssVar,#subrunoffVar,#runoffVar,#canwVar,#ssiVar').removeClass('hidden');
    };
});

$(function () {
    $btnLoadWatershed = $('#btn-load-watershed');
    getHSWatershedList();
    $btnLoadWatershed.on('click', onClickLoadWatershed);
    $popupLoadWatershed = $('#popup-load-watershed');

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

    mapView = map.getView();

    if (window.location.search.includes('?')) {
        var query = window.location.search.split("&");

        var qConfig = query[0].substring(query[0].lastIndexOf("config=") + 7);
        var qGeom = query[1].substring(query[1].lastIndexOf("geom=") + 5);
        var qVar = query[2].substring(query[2].lastIndexOf("variable=") + 9);
        if (qGeom === 'channel_rt' || qGeom === 'reservoir') {
            var qCOMID = Number(query[3].substring(query[3].lastIndexOf("COMID=") + 6));
            var qLong = Number(query[4].substring(query[4].lastIndexOf("longitude=")+10));
            var qLat = Number(query[5].substring(query[5].lastIndexOf("latitude=")+9));
            var qDate = query[6].substring(query[6].lastIndexOf("startDate=") + 10);
            var qTime = query[7].substring(query[7].lastIndexOf("time=") + 5);
        } else {
            var qCOMID = query[3].substring(query[3].lastIndexOf("Y=") + 2) + ',' +
                query[4].substring(query[4].lastIndexOf("X=") + 2);
            var qLong = Number(query[5].substring(query[5].lastIndexOf("longitude=")+10));
            var qLat = Number(query[6].substring(query[6].lastIndexOf("latitude=")+9));
            var qDate = query[7].substring(query[7].lastIndexOf("startDate=") + 10);
            var qTime = query[8].substring(query[8].lastIndexOf("time=") + 5);
        }

        var qLag = [];
        var qDateEnd = query[query.length - 3].substring(query[query.length - 3].lastIndexOf("endDate=") + 8);

        $('#config').val(qConfig);
        $('#geom').val(qGeom);

        if (window.location.search.indexOf('00z') > -1) {
            qLag.push('00z');
            $('#00z').attr('checked', true);
            $('#00z').parent().parent().removeClass('bootstrap-switch-off')
        } else {
            $('#00z').attr('checked', false);
            $('#00z').parent().parent().addClass('bootstrap-switch-off')
        }
        if (window.location.search.indexOf('06z') > -1) {
            qLag.push('06z');
            $('#06z').attr('checked', true);
            $('#06z').parent().parent().removeClass('bootstrap-switch-off')
        }
        if (window.location.search.indexOf('12z') > -1) {
            qLag.push('12z');
            $('#12z').attr('checked', true);
            $('#12z').parent().parent().removeClass('bootstrap-switch-off')
        }
        if (window.location.search.indexOf('18z') > -1) {
            qLag.push('18z');
            $('#18z').attr('checked', true);
            $('#18z').parent().parent().removeClass('bootstrap-switch-off')
        }

        if (qGeom === 'channel_rt' || qGeom === 'reservoir') {
            $('#comidInput').val(qCOMID);
        } else if (qGeom === 'land') {
            $('#gridInputY').val(qCOMID.split(',')[0]);
            $('#gridInputX').val(qCOMID.split(',')[1]);
        }

        $('#longInput').val(qLong);
        $('#latInput').val(qLat);
        $('#startDate').val(qDate);
        $('#time').val(qTime);

        if ($('#longInput').val() !== '-98' && $('#latInput').val() !== '38.5') {
            CenterMap(qLat, qLong);
            mapView.setZoom(12);

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
        }

        initChart(qConfig, startDate, seriesData);

        get_netcdf_chart_data(qConfig, qGeom, qVar, qCOMID, qDate, qTime, qLag, qDateEnd);
    }

    $("#config").trigger("change");
    $("#geom").trigger("change");

    /**********************************
     ********INITIALIZE LAYERS*********
     **********************************/

    var lonlat;
    map.on('click', function(evt) {
        var coordinate = evt.coordinate;
        lonlat = ol.proj.transform(coordinate, 'EPSG:3857', 'EPSG:4326');
        if (mapView.getZoom()<12) {
            mapView.setZoom(12);
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
    mapView.setCenter(coords);
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
    mapView.setZoom(4);
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

function get_netcdf_chart_data(config, geom, variable, comid, date, time, lag, endDate) {
    $.ajax({
        type: 'GET',
        url: 'get-netcdf-data',
        dataType: 'json',
        data: {
            'config': config,
            'geom': geom,
            'variable': variable,
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
        beforeSend: function () {
            $('#info').html('<p class="alert alert-info" style="text-align: center"><strong>' +
                'Retrieving forecasts' + '</strong></p>').removeClass('hidden');
        },
        complete: function () {
            setTimeout(function () {
                $('#info').addClass('hidden')
            }, 5000);
        },
        success: function (data) {
            if ("success" in data) {
                if ("ts_pairs_data" in data) {
                    var returned_tsPairsData = JSON.parse(data.ts_pairs_data);
                    for (var key in returned_tsPairsData) {
                        if (returned_tsPairsData[key][2] === 'notLong') {
                            var d = new Date(0);
                            startDate = d.setUTCSeconds(returned_tsPairsData[key][0]);
                            seriesData = returned_tsPairsData[key][1];
                            nc_chart.yAxis[0].setExtremes(null, null);
                            plotData(config, geom, variable, seriesData, startDate);
                        } else {

                            for (j = 0; j < returned_tsPairsData[key].length; j++) {
                                var d = new Date(0);
                                var startDateG = d.setUTCSeconds(returned_tsPairsData[key][j][0]);
                                for (i = 1; i < returned_tsPairsData[key][j].length - 1; i++) {
                                    var seriesDataTemp = returned_tsPairsData[key][j][i];
                                    var seriesDesc = 'Member 0' + String(i) + ' ' +
                                        returned_tsPairsData[key][j][returned_tsPairsData[key][j].length - 1];
                                    seriesDataGroup.push([seriesDataTemp, seriesDesc, startDateG]);
                                    nc_chart.yAxis[0].setExtremes(null, null);
                                    plotData(config, geom, variable, seriesDataTemp, startDateG, i - 1, seriesDesc);
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
                title: {text: 'Flow (cfs)'},
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
                            changeUnits(config)
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
                title: {text: 'Flow (cfs)'},
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
                            changeUnits(config)
                        }
                    }
                }
            }
        };

        $('#nc-chart').highcharts(default_chart_settings);
        nc_chart = $('#nc-chart').highcharts();
    };
}

var plotData = function(config, geom, variable, data, start, colorIndex, seriesDesc) {
    $('#actionBtns').removeClass('hidden');
    var calib = calibrateModel(config, start)

    if (variable === 'streamflow' || variable === 'inflow' || variable === 'outflow') {
        var units = 'Flow (cfs)';
    } else if (variable === 'velocity') {
        var units = 'Velocity (ft/s)';
        nc_chart.yAxis[0].setTitle({text: units});
        $('tspan:contains("Change Units")').parent().parent().attr('hidden', true);
    } else if (variable === 'SNOWH') {
        var units = 'Snow Depth (Feet)';
        nc_chart.yAxis[0].setTitle({text: units});
        $('tspan:contains("Change Units")').parent().parent().attr('hidden', true);
    } else if (variable === 'SNEQV') {
        var units = 'Snow Water Equivalent (Feet)';
        nc_chart.yAxis[0].setTitle({text: units});
        $('tspan:contains("Change Units")').parent().parent().attr('hidden', true);
    } else if (variable === 'ACCET' || variable === 'ACCECAN' || variable === 'CANWAT' ||
        variable === 'UGDRNOFF' || variable === 'SFCRNOFF') {
        var units = 'Depth (Inches)';
        nc_chart.yAxis[0].setTitle({text: units});
        $('tspan:contains("Change Units")').parent().parent().attr('hidden', true);
    } else if (variable === 'FSNO') {
        var units = 'Snow Cover (Fraction)';
        nc_chart.yAxis[0].setTitle({text: units});
        $('tspan:contains("Change Units")').parent().parent().attr('hidden', true);
    } else if (variable === 'SOIL_M') {
        var units = 'Soil Moisture';
        nc_chart.yAxis[0].setTitle({text: units});
        $('tspan:contains("Change Units")').parent().parent().attr('hidden', true);
    } else if (variable === 'SOILSAT_TOP' || variable === 'SOILSAT') {
        var units = 'Soil Saturation (Fraction)';
        nc_chart.yAxis[0].setTitle({text: units});
        $('tspan:contains("Change Units")').parent().parent().attr('hidden', true);
    } else if (variable === 'SNOWT_AVG' || variable === 'SOIL_T') {
        var units = 'Temperature (Kelvin)';
        nc_chart.yAxis[0].setTitle({text: units});
        $('tspan:contains("Change Units")').parent().parent().attr('hidden', true);
    };

    if (config !== 'long_range') {
        var data_series = {
            type: 'area',
            name: units,
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
            name: seriesDesc + ' ' + units,
            data: data,
            pointStart: start + (3600 * 1000 * 6),
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

function changeUnits(config) {
    if (config !== 'long_range') {
        var calib = calibrateModel(config, startDate);
        if (nc_chart.yAxis[0].axisTitle.textStr === 'Flow (cfs)') {
            var newSeries = [];
            seriesData.forEach(function (i) {
                newSeries.push(i * 0.0283168);
            });

            nc_chart.series[0].remove();
            nc_chart.yAxis[0].setTitle({
                text: 'Flow (cms)'
            });
            var data_series = {
                type: 'area',
                name: 'Flow (cms)',
                data: newSeries,
                pointStart: calib['start'],
                pointInterval: calib['interval']
            };
            nc_chart.addSeries(data_series);
        } else {
            nc_chart.series[0].remove();
            nc_chart.yAxis[0].setTitle({text: 'Flow (cfs)'});
            var data_series = {
                type: 'area',
                name: 'Flow (cfs)',
                data: seriesData,
                pointStart: calib['start'],
                pointInterval: calib['interval']
            };
            nc_chart.addSeries(data_series);
        };
    } else {
        if (nc_chart.yAxis[0].axisTitle.textStr === 'Flow (cfs)') {
            while(nc_chart.series.length > 0) {
                nc_chart.series[0].remove(true);
            }
            nc_chart.yAxis[0].setTitle({text: 'Flow (cms)'});

            for (i = 0; i < seriesDataGroup.length; i++) {
                var newSeries = [];
                seriesDataGroup[i][0].forEach(function (j) {
                    newSeries.push(j * 0.0283168);
                });
                var calib = calibrateModel(config);
                var data_series = {
                    type: 'area',
                    name: seriesDataGroup[i][1] + ' Flow (cms)',
                    data: newSeries,
                    pointStart: seriesDataGroup[i][2] + (3600 * 1000 * 6),
                    pointInterval: calib['interval']
                };
                nc_chart.addSeries(data_series);
            };
        } else {
            while(nc_chart.series.length > 0) {
                nc_chart.series[0].remove(true);
            }
            nc_chart.yAxis[0].setTitle({text: 'Flow (cfs)'});

            for (i = 0; i < seriesDataGroup.length; i++) {
                var calib = calibrateModel(config)
                var data_series = {
                    type: 'area',
                    name: seriesDataGroup[i][1] + ' Flow (cfs)',
                    data: seriesDataGroup[i][0],
                    pointStart: seriesDataGroup[i][2] + (3600 * 1000 * 6),
                    pointInterval: calib['interval']
                };
                nc_chart.addSeries(data_series);
            };
        };
    };
};

function calibrateModel(config, date) {
    var interval;
    var start;
    if (config === 'short_range') {
        interval = 3600 * 1000; // one hour
        start = date + (3600 * 1000); // calibrates short range;
    } else if (config === 'analysis_assim') {
        interval = 3600 * 1000; // one hour
        start = date + (3600 * 1000 * 3); // calibrates analysis assimilation
    } else if (config === 'medium_range') {
        interval = 3600 * 1000 * 3; // three hours
        start = date + (3600 * 1000 * 3); // calibrates medium range;
    } else {
        interval = 3600 * 1000 * 6; // six hours
    };
    return {'interval': interval, 'start': start}
}

function getHSWatershedList () {
    $.ajax({
        type: 'GET',
        url: 'get-hs-watershed-list',
        dataType: 'json',
        success: function (response) {
            var resources,
                resTableHtml = '<table id="tbl-watersheds"><thead><th></th><th>Title</th><th>Owner</th></thead><tbody>';

            if (response.hasOwnProperty('success')) {
                if (response.hasOwnProperty('resources')) {
                    resources = JSON.parse(response.resources);
                    if (resources.length === 0) {
                        $popupLoadWatershed.find('.modal-body').html('<b>It appears that you do not own any valid HydroShare resources.</b>');
                    } else {
                        resources.forEach(function (resource) {
                            resTableHtml += '<tr>' +
                                '<td><input type="radio" name="resource" class="rdo-res" data-filename="' + resource.filename + '" value="' + resource.id + '"></td>' +
                                '<td class="res_title">' + resource.title + '</td>' +
                                '<td class="res_owner">' + resource.owner + '</td>' +
                                '</tr>';
                        });
                        resTableHtml += '</tbody></table>';
                        $popupLoadWatershed.find('.modal-body').html(resTableHtml);
                        $btnLoadWatershed
                            .removeClass('hidden')
                            .prop('disabled', false);
                    }
                }
            } else if (response.hasOwnProperty('error')) {
                $popupLoadWatershed.find('.modal-body').html('<h6>' + response.error + '</h6>');
            }
        }
    });
}

function onClickLoadWatershed() {

    $btnLoadWatershed.prop('disabled', true);
    var $rdoRes = $('.rdo-res:checked');
    var resId = $rdoRes.val();
    var filename = $rdoRes.attr('data-filename');

    loadWatershed(resId, filename);
}

function loadWatershed(resId, filename) {
    $.ajax({
        type: 'GET',
        url: 'load-watershed',
        dataType: 'json',
        data: {
            res_id: resId,
            filename: filename
        },
        error: function () {
            console.error('Failed to load watershed!');
        },
        success: function (watershed) {
            if (watershed.hasOwnProperty('success')) {
                addGeojsonLayerToMap(watershed.geojson_str, watershed.proj_str, watershed.id, true);
                $popupLoadWatershed.modal('hide');
            } else {
                alert(watershed.error);
            }
            $btnLoadWatershed.prop('disabled', false);
        }
    });
}

function addGeojsonLayerToMap(geojsonStr, projStr, watershedId, zoomTo) {
    var geoJson;
    var geometry;
    var watershedLayer;
    var geoJsonReproj;

    geojsonStr = geojsonStr.replace(/&quot;/g, '"'); // Unencode the encoded double-quotes

    geoJson = JSON.parse(geojsonStr);

    if (!(projStr === null || projStr === undefined || projStr === '')) {
        projStr = projStr.replace(/&quot;/g, '"'); // Unencode the encoded double-quotes
        proj4.defs('new_projection', projStr);
        if (projStr) {
            geoJsonReproj = reproject(geoJson, proj4('new_projection'), proj4('EPSG:3857'));
            watershedLayer = new ol.layer.Vector({
                source: new ol.source.Vector({
                    features: (new ol.format.GeoJSON()).readFeatures(geoJsonReproj)
                })
            });
        }
    } else {
        geometry = new ol.format.GeoJSON({
            defaultDataProjection: 'EPSG:3857'
        }).readGeometry(geoJson);
        geometry.transform('EPSG:4326', 'EPSG:3857');
        watershedLayer = new ol.layer.Vector({
            source: new ol.source.Vector({
                features: [
                    new ol.Feature(geometry)
                ]
            })
        });
    }

    map.addLayer(watershedLayer);
    if (zoomTo) {
        mapView.fit(watershedLayer.getSource().getExtent(), map.getSize());
    }
    $('#input-watershed-id').val(watershedId);
}