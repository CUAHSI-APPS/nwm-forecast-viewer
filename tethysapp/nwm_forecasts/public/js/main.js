$(document).ready(function () {
    if (!window.location.search.includes('?'))
    {
        $("#welcome-popup").modal("show");
    }

});

//Map variables
var map, mapView, base_layer, all_streams_layer, selected_streams_layer, watershedLayer;

// NHD variables
var comid;

//Chart variables
var nc_chart, seriesData, startDate, seriesDataGroup = [];

//jQuery handle variables
var $btnLoadWatershed;
var $popupLoadWatershed;

(function () {
    var target, observer, config;
    // select the target node
    target = $('#app-content-wrapper')[0];

    observer = new MutationObserver(function () {
        window.setTimeout(function () {
            map.updateSize();
        }, 350);
    });

    config = {attributes: true};

    observer.observe(target, config);
}());

function change_time_dropdown_content(config)
{
    var newOptions;
    if (config=="short_range")
    {
          newOptions = {"00:00": "00",
                          "01:00": "01",
                          "02:00": "02",
                          "03:00": "03",
                          "04:00": "04",
                          "05:00": "05",
                          "06:00": "06",
                          "07:00": "07",
                          "08:00": "08",
                          "09:00": "09",
                          "10:00": "10",
                          "11:00": "11",
                          "12:00": "12",
                          "13:00": "13",
                          "14:00": "14",
                          "15:00": "15",
                          "16:00": "16",
                          "17:00": "17",
                          "18:00": "18",
                          "19:00": "19",
                          "20:00": "20",
                          "21:00": "21",
                          "22:00": "22",
                          "23:00": "23"};
    }
    else if (config=="medium_range")
    {
         newOptions = {"00:00": "00",
                          "06:00": "06",
                          "12:00": "12",
                          "18:00": "18"};
    }
    else
    {
        return ;
    }


    var $el = $("#time");
    var selected_value = $el.val();
    $el.empty(); // remove old options
    $.each(newOptions, function(key,value) {
        $el.append($("<option></option>")
        .attr("value", value).text(key));
    });
    $el.val(selected_value);
    if ($el.val() == null)
    {
        $el.val("00");
    }
}

$('#config').on('change', function () {

    if ($('#config').val() != 'analysis_assim')
    {
        $("#geom option[value='forcing']").attr('disabled','disabled');
        if ($("#geom option:selected").val() == "forcing" ||  $("#geom").val()=="forcing")
        {
            $("#geom option[value='channel_rt']").attr("selected", "selected");
            $("#geom").val('channel_rt');
        }
    }
    else
    {
        $("#geom option[value='forcing']").removeAttr('disabled');
    }

    if ($('#config').val() === 'medium_range')
    {
        $('#endDate,#endDateLabel, #timeLag').addClass('hidden');
        change_time_dropdown_content($('#config').val());
        $('#time').parent().removeClass('hidden');
        if ($('#geom').val() === 'channel_rt' && $('#config').val() !== 'long_range')
        {
            $('#velocVar').removeClass('hidden');
        }
    }
    else if ($('#config').val() === 'long_range')
    {
        $('#endDate,#endDateLabel,#velocVar').addClass('hidden');
        $('#time').parent().addClass('hidden');
        $('#timeLag').removeClass('hidden');
    }
    else if ($('#config').val() === 'short_range')
    {
        $('#endDate,#endDateLabel,#timeLag').addClass('hidden');
        change_time_dropdown_content($('#config').val());
        $('#time').parent().removeClass('hidden');
        if ($('#geom').val() === 'channel_rt' && $('#config').val() !== 'long_range') {
            $('#velocVar').removeClass('hidden');
        };
    }
    else if ($('#config').val() === 'analysis_assim')
    {
        $('#endDate,#endDateLabel').removeClass('hidden');
        $('#time').parent().addClass('hidden');
        $('#timeLag').addClass('hidden');
        if ($('#geom').val() === 'channel_rt' && $('#config').val() !== 'long_range')
        {
            $('#velocVar').removeClass('hidden');
        }
    }
    $("#geom").trigger("change");
});

$(function () {
    //turns toggle navigation icon off
//    $(".toggle-nav").removeClass('toggle-nav');

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

    if (window.location.search.includes('?'))
    {
        //var query = window.location.search.split("&");

        var qConfig = getUrlParameter('config', null);
        $('#config').val(qConfig);
        change_time_dropdown_content(qConfig);
        var qGeom = getUrlParameter('geom', null);
        $('#geom').val(qGeom);
        var qVar = getUrlParameter('variable', null);
        $('#variable').val(qVar);
        var qLat = Number(getUrlParameter('latitude', null));
        $('#latInput').val(qLat);
        var qLong = Number(getUrlParameter('longitude', null));
        $('#longInput').val(qLong);
        var qDate = getUrlParameter("startDate", null);
        $('#startDate').val(qDate);
        var qTime = getUrlParameter("time", null);
        $('#time').val(qTime);
        if (qGeom === 'channel_rt' || qGeom === 'reservoir')
        {
            var qCOMID = getUrlParameter('COMID', null);
            $('#comidInput').val(qCOMID);
        }
        else
        {
            var qCOMID = getUrlParameter("Y", null) + ',' +  getUrlParameter("X", null);
            $('#gridInputY').val(qCOMID.split(',')[0]);
            $('#gridInputX').val(qCOMID.split(',')[1]);
        }
        var qDateEnd = getUrlParameter("endDate", null);
        $('#endDate').val(qDateEnd);
        var qLag = [];
        if (window.location.search.indexOf('00z') > -1)
        {
            qLag.push('00z');
            $('#00z').attr('checked', true);
            $('#00z').parent().parent().removeClass('bootstrap-switch-off')
        }
        else
        {
            $('#00z').attr('checked', false);
            $('#00z').parent().parent().addClass('bootstrap-switch-off')
        }
        if (window.location.search.indexOf('06z') > -1)
        {
            qLag.push('06z');
            $('#06z').attr('checked', true);
            $('#06z').parent().parent().removeClass('bootstrap-switch-off')
        }
        if (window.location.search.indexOf('12z') > -1)
        {
            qLag.push('12z');
            $('#12z').attr('checked', true);
            $('#12z').parent().parent().removeClass('bootstrap-switch-off')
        }
        if (window.location.search.indexOf('18z') > -1)
        {
            qLag.push('18z');
            $('#18z').attr('checked', true);
            $('#18z').parent().parent().removeClass('bootstrap-switch-off')
        }


        if (($('#longInput').val() !== '-98' && $('#latInput').val() !== '38.5') && qGeom!== 'channel_rt')
        {
            CenterMap(qLat, qLong);
            mapView.setZoom(12);
            lonlat = [qLong, qLat];
            run_point_indexing_service2(lonlat);
        }
        if (qCOMID && qGeom === 'channel_rt')
        {
            $.ajax({
                url: 'https://watersgeo.epa.gov/arcgis/rest/services/NHDPlus_NP21/NHDSnapshot_NP21_Labeled/MapServer/0/query',
                data: {
                    where: 'COMID=' + qCOMID,
                    returnGeometry: true,
                    f: 'json'
                },
                dataType: 'json',
                success: function (data) {
                    var geometry = data.features[0].geometry;
                    geometry['coordinates'] = geometry['paths'][0];
                    delete geometry['paths'];
                    geometry['type'] = 'LineString';
                    selected_streams_layer.getSource().clear();
                    var geojsonformatter = new ol.format.GeoJSON;
                    var myGeometry = geojsonformatter.readGeometry(geometry);
                    //name the feature according to COMID
                    var newFeatureName = 'COMID: ' + comid;

                    var newFeature = new ol.Feature({
                        geometry: myGeometry,
                        name: newFeatureName
                    });
                    selected_streams_layer.getSource().addFeature(newFeature);
                    var newLon = geometry.coordinates[Math.floor(geometry.coordinates.length / 2)][0];
                    var newLat = geometry.coordinates[Math.floor(geometry.coordinates.length / 2)][1];
                    lonlat = ol.proj.transform([newLon, newLat], 'EPSG:3857', 'EPSG:4326');
                    $('#longInput').val(lonlat[0]);
                    $('#latInput').val(lonlat[1]);
                    CenterMap(lonlat[1], lonlat[0]);
                    mapView.setZoom(12);
                } //success: function (data)
            }); //$.ajax(
        }//if (qCOMID)
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
        if ($("#geom").val() == "channel_rt") {
        }
    });

    base_layer = new ol.layer.Tile({
        source: new ol.source.BingMaps({
            key: 'eLVu8tDRPeQqmBlKAjcw~82nOqZJe2EpKmqd-kQrSmg~AocUZ43djJ-hMBHQdYDyMbT-Enfsk0mtUIGws1WeDuOvjY4EXCH-9OK3edNLDgkc',
            imagerySet: 'AerialWithLabels'
        })
    });

    var grid_Source = new ol.source.TileWMS({
        url: 'https://geoserver.byu.edu/arcgis/services/NWM/grid/MapServer/WmsServer?',
        params: {
            LAYERS: "0",
        },
        crossOrigin: 'Anonymous' //This is necessary for CORS security in the browser
    });

    grid = new ol.layer.Tile({
        source: grid_Source,
        maxResolution: 100,
        keyword: "land"
    });

    grid.setOpacity(0.4);

    var reservoir_Source = new ol.source.TileWMS({
        url: 'https://geoserver.byu.edu/arcgis/services/NWM/reservoir/MapServer/WmsServer?',
        params: {
            LAYERS: "0",
        },
        crossOrigin: 'Anonymous' //This is necessary for CORS security in the browser
    });

    reservoir = new ol.layer.Tile({
        source: reservoir_Source,
        keyword: "reservoir"
    });

    var createLineStyleFunction = function() {
        return function(feature, resolution) {
            var style = new ol.style.Style({
                stroke: new ol.style.Stroke({
                    color: '#ffff00',
                    width: 2
                }),
//                text: new ol.style.Text({
//                    textAlign: 'center',
//                    textBaseline: 'middle',
//                    font: 'bold 12px Verdana',
//                    text: getText(feature, resolution),
//                    fill: new ol.style.Fill({
//                        color: '#cc00cc'
//                    }),
//                    stroke: new ol.style.Stroke({
//                        color: 'black',
//                        width: 0.5
//                    })
//                })
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
        style: createLineStyleFunction(),
        keyword: 'selected_streams_layer'
    });

    var serviceUrl = 'https://watersgeo.epa.gov/arcgis/rest/services/NHDPlus_NP21/NHDSnapshot_NP21_Labeled/MapServer/0';
    // var serviceUrl = 'http://geoserver.byu.edu/arcgis/rest/services/NWC/NWM_Geofabric/MapServer/1';
    var esrijsonFormat = new ol.format.EsriJSON();
    var vectorSource = new ol.source.Vector({
        loader: function(extent, resolution, projection) {
            var url = serviceUrl + '/query/?f=json&geometry=' +
                '{"xmin":' + extent[0] + ',"ymin":' + extent[1] + ',"xmax":' + extent[2] + ',"ymax":' + extent[3] +
                ',"spatialReference":{"wkid":102100}}&inSR=102100&outSR=102100';
            $.ajax({
                url: url,
                dataType: 'jsonp',
                success: function(response) {
                    if (response.error)
                    {
                        alert(response.error.message + '\n' +
                            response.error.details.join('\n'));
                    }
                    else
                    {
                        // dataProjection will be read from document
                        var features = esrijsonFormat.readFeatures(response, {
                            featureProjection: projection
                        });
                        if (features.length > 0)
                        {
                            vectorSource.addFeatures(features);
                        }
                    }
                }
            });
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
            }),
        }),
        maxResolution: 100,
        keyword: 'channel_rt'
    });

    watershedLayer =  new ol.layer.Vector(
        {
        source: new ol.source.Vector(),
        keyword: 'watershedLayer',
            style: new ol.style.Style({stroke:new ol.style.Stroke({ color: '#ffffff',
                width: 2}), fill: new ol.style.Fill({ color: [255,0,255,0.5]})})
        }
    );

    map.addLayer(base_layer);
    map.addLayer(watershedLayer);
    map.addLayer(grid);
    map.addLayer(reservoir);
    map.addLayer(all_streams_layer);
    map.addLayer(selected_streams_layer);


    toggleLayers = [grid, reservoir, all_streams_layer, selected_streams_layer];

    var element = document.getElementById('popup');

    var popup = new ol.Overlay({
        element: element,
        positioning: 'bottom-center',
        stopEvent: true
    });

    map.addOverlay(popup);

    //Click funtion to choose gauge on map
    map.on('singleclick', function(evt) {
        $(element).popover('destroy');
        // if ((map.getTargetElement().style.cursor == "pointer")) {
            var view = map.getView();
            var viewResolution = view.getResolution();

            if (grid.getVisible())
            {
                var grid_url = grid_Source.getGetFeatureInfoUrl(evt.coordinate, viewResolution, view.getProjection(), {
                    'INFO_FORMAT': 'text/xml',
                    'FEATURE_COUNT': 1
                });
            }
            else if (reservoir.getVisible())
            {
                var reservoir_url = reservoir_Source.getGetFeatureInfoUrl(evt.coordinate, viewResolution, view.getProjection(), {
                    'INFO_FORMAT': 'text/xml',
                    'FEATURE_COUNT': 1
                });
            }

            // }
            var displayContent = "<table>";
            var showPopup = false;
            var zoomToClick = false;
//            var displayContent = "COMID: " + comid;
            if (grid_url)
            {
                var grid_Data = dataCall(grid_url);
                var grid_Count = grid_Data.documentElement.childElementCount;

                //This is for the land grid
                for (var i = 0; i < grid_Count; i++)
                {
                    var south_north = grid_Data.documentElement.children[i].attributes['south_north'].value;
                    var west_east = grid_Data.documentElement.children[i].attributes['west_east'].value;
                    var lon_layer = grid_Data.documentElement.children[i].attributes['XLONG_M'].value;
                    var lat_layer = grid_Data.documentElement.children[i].attributes['XLAT_M'].value;
                    console.log(lon_layer);
                    console.log(lat_layer);

                    $("#gridInputY").val(south_north);
                    $("#gridInputX").val(west_east);


                    displayContent += '<tr><td>south_north: ' + south_north + '</td><td>west_east: ' + west_east + '</td></tr>';
                    showPopup = true;
                    zoomToClick = true;
                }
            }
            else if (reservoir_url)
            {
                var reservoir_Data = dataCall(reservoir_url);
                var reservoir_Count = reservoir_Data.documentElement.childElementCount;
                if (reservoir_Count < 1)
                {
                    return;
                }
                //This is for the reservoirs
                for (i = 0; i < reservoir_Count; i++)
                {
                    var reservoirID = reservoir_Data.documentElement.children[i].attributes['lake_id'].value;
                    $("#comidInput").val(reservoirID);

                    displayContent += '<tr><td>Reservoir COMID: ' + reservoirID + '</td></tr>';
                }
                showPopup = true;
                zoomToClick = false;

                var coordinate = evt.coordinate;
                lonlat = ol.proj.transform(coordinate, 'EPSG:3857', 'EPSG:4326');
            }
            displayContent += '</table>';

            if (showPopup)
            {
                var clickCoord = evt.coordinate;
                lonlat = ol.proj.transform(clickCoord, 'EPSG:3857', 'EPSG:4326');
                console.log(lonlat);
                popup.setPosition(clickCoord);
                $(element).popover({
                    'placement': 'top',
                    'html': true,
                    'content': displayContent
                });

                $(element).popover('show');
                $(element).next().css('cursor', 'text');
            }

            if ($("#geom").val() == "channel_rt") {
                    var coordinate = evt.coordinate;
                    lonlat = ol.proj.transform(coordinate, 'EPSG:3857', 'EPSG:4326');
                    if (mapView.getZoom() < 12) {
                        mapView.setZoom(12);
                        CenterMap(lonlat[1], lonlat[0]);
                    }
                    run_point_indexing_service(lonlat);
                }

            if ($("#geom").val() == "land")
            {
                    var coordinate = evt.coordinate;
                    lonlat = ol.proj.transform(coordinate, 'EPSG:3857', 'EPSG:4326');
                    if (mapView.getZoom() < 12) {
                        mapView.setZoom(12);
                        CenterMap(lonlat[1], lonlat[0]);
                    }
            }
            $('#longInput').val(lonlat[0]);
            $('#latInput').val(lonlat[1]);
    });

    map.on('pointermove', function(evt) {
        if (evt.dragging) {
            return;
        }
        var pixel = map.getEventPixel(evt.originalEvent);
        var hit = map.forEachLayerAtPixel(pixel, function(layer) {
            if (layer != base_layer) {
                return true;
            }
        });
        map.getTargetElement().style.cursor = hit ? 'pointer' : '';
    });

    $('#geom').on('change', function () {

    // switch layers
    toggleLayers.forEach(function(layer) {
            layer.setVisible($("#geom").val() === layer.get('keyword'));
        });
    if ($("#geom").val() == 'channel_rt')
    {
        selected_streams_layer.setVisible(true);
    }
    else if ($("#geom").val() == 'forcing')
    {
        grid.setVisible(true);
    }

    // hide all variable options in variable dropdown list (display them later)
    $("#variable option").each(function()
    {
        $(this).addClass('hidden')
    });

    // hide and disable coordinate input
        $('#gridDiv').addClass('hidden');
        // $('#gridInputY').attr('disabled', true);
        // $('#gridInputX').attr('disabled', true);
    // hide and disable comid input
        $('#comidDiv').addClass('hidden');
        // $('#comidInput').attr('disabled', true);

    if ($('#geom').val() === 'channel_rt')
    {
        if (window.location.search.includes('channel_rt') && window.location.search.includes('long_range') === false)
        {
            $('#variable').val(getUrlParameter('variable', null));
        }
        else
        {
            $('#variable').val('streamflow');
        }

        $('#comidDiv').removeClass('hidden');
        $('#comidInput').attr('disabled', false);
        $('#streamVar').removeClass('hidden');

        if ($('#config').val() !== 'long_range')
        {
            $('#velocVar').removeClass('hidden');
        }
        // $('#gridInputY').attr('disabled', true);
        // $('#gridInputX').attr('disabled', true);
        // $('#gridDiv,#infVar,#outfVar,#snowhVar,#sneqVar,#snowcVar,#etVar,#ssVar,#avsnowVar,#subrunoffVar,#runoffVar,#canwVar,#ssiVar,#evapVar,#soiltVar,#soilmVar').
        //     addClass('hidden');
    }
    else if ($('#geom').val() === 'reservoir')
    {
        if (window.location.search.includes('reservoir'))
        {
            //$('#variable').val(window.location.search.split("&")[2].substring(window.location.search.split("&")[2].
            //    lastIndexOf("variable=") + 9));
            $('#variable').val(getUrlParameter('variable', null));
        }
        else
        {
            $('#variable').val('inflow');
        }
        $('#comidInput').attr('disabled', false);
        $('#comidDiv').removeClass('hidden');
        $('#infVar,#outfVar').removeClass('hidden');
        // $('#gridInputY').attr('disabled', true);
        // $('#gridInputX').attr('disabled', true);
        // $('#gridDiv,#streamVar,#velocVar,#snowhVar,#sneqVar,#snowcVar,#etVar,#ssVar,#avsnowVar,#subrunoffVar,#runoffVar,#canwVar,#ssiVar,#evapVar,#soiltVar,#soilmVar').
        //     addClass('hidden');
    }
    else if ($('#geom').val() === 'land' && ($('#config').val() === 'short_range' ||
        $('#config').val() === 'analysis_assim'))
    {
        // $('#comidInput').attr('disabled', true);
        // $('#comidDiv,#streamVar,#velocVar,#infVar,#outfVar,#subrunoffVar,#runoffVar,#evapVar,#soiltVar,#soilmVar,#canwVar,#ssiVar')
        //     .addClass('hidden');

        $('#gridDiv').removeClass('hidden');
        $('#gridInputY').attr('disabled', false);
        $('#gridInputX').attr('disabled', false);
        if (window.location.search.includes('land'))
        {
            // $('#variable').val(window.location.search.split("&")[2].substring(window.location.search.split("&")[2].
            //     lastIndexOf("variable=") + 9));
            $('#variable').val(getUrlParameter('variable', null));
        }
        else
        {
            $('#variable').val('SNOWH');
        }
        $('#snowhVar,#sneqVar,#snowcVar,#etVar,#ssVar,#avsnowVar').removeClass('hidden');
    }
    else if ($('#geom').val() === 'land' && $('#config').val() === 'medium_range')
    {
        // $('#comidInput').attr('disabled', true);
        // $('#comidDiv,#streamVar,#velocVar,#infVar,#outfVar,#runoffVar,#ssiVar').
        //     addClass('hidden');

        $('#gridDiv').removeClass('hidden');
        $('#gridInputY').attr('disabled', false);
        $('#gridInputX').attr('disabled', false);
        if (window.location.search.includes('land'))
        {
            // $('#variable').val(window.location.search.split("&")[2].substring(window.location.search.split("&")[2].
            //     lastIndexOf("variable=") + 9));
            $('#variable').val(getUrlParameter('variable', null));
        }
        else
        {
            $('#variable').val('SNOWH');
        }
        $('#snowhVar,#sneqVar,#snowcVar,#etVar,#ssVar,#avsnowVar,#subrunoffVar,#evapVar,#canwVar,#soiltVar,#soilmVar').
            removeClass('hidden');
    }
    else if ($('#geom').val() === 'land' && $('#config').val() === 'long_range')
    {
        // $('#comidInput').attr('disabled', true);
        // $('#comidDiv,#streamVar,#velocVar,#infVar,#outfVar,#snowhVar,#snowcVar,#avsnowVar,#evapVar,#soiltVar,#soilmVar, #rainrateVar')
        //     .addClass('hidden');

        $('#gridDiv').removeClass('hidden');
        $('#gridInputY').attr('disabled', false);
        $('#gridInputX').attr('disabled', false);
        if (window.location.search.includes('land') && window.location.search.includes('long_range'))
        {
            // $('#variable').val(window.location.search.split("&")[2].substring(window.location.search.split("&")[2].
            //     lastIndexOf("variable=") + 9));
            $('#variable').val(getUrlParameter('variable', null));
        }
        else
        {
            $('#variable').val('SNEQV');
        }
        $('#sneqVar,#etVar,#ssVar,#subrunoffVar,#runoffVar,#canwVar,#ssiVar').removeClass('hidden');
    }
    else if ($('#geom').val() === 'forcing' && $('#config').val() === 'analysis_assim')
    {
        // $('#comidInput').attr('disabled', true);
        // $('#comidDiv,#streamVar,#velocVar,#infVar,#outfVar,#snowhVar,#snowcVar,#avsnowVar,#evapVar,#soiltVar,#soilmVar')
        //     .addClass('hidden');
        $('#gridDiv').removeClass('hidden');
        $('#gridInputY').attr('disabled', false);
        $('#gridInputX').attr('disabled', false);
        if (window.location.search.includes('forcing') && window.location.search.includes('analysis_assim'))
        {
            $('#variable').val(getUrlParameter('variable', null));
        }
        else
        {
            $('#variable').val('RAINRATE');
        }
        $('#rainrateVar').removeClass('hidden');
    }

}); //  $('#geom').on('change', function (){})

    var watershed_geojson_str = $("#watershed_geojson_str").val();
    if (watershed_geojson_str.length > 0)
    {
        addGeojsonLayerToMap(watershed_geojson_str, "234", false);
    }
    $("#geom").trigger("change");

});

/****************************
 ***Popup Displaying Info***
 ****************************/

function dataCall(inputURL) {
    var result = null;
    $.ajax({
        url: inputURL,
        async: false,
    }).then(function(response) {
        result = response;
    });
    return result;
}

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

function run_point_indexing_service2(lonlat)
{
    var qLong = lonlat[0];
    var qLat = lonlat[1];
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

function pis_success(result) {
    var srv_rez = result.output;
    if (srv_rez == null) {
        if (result.status.status_message !== null) {
            report_failed_search(result.status.status_message);
        } else {
            report_failed_search("No reach located near your click point.");
        }
        return;
    }

    var srv_fl = result.output.ary_flowlines;
    var newLon = srv_fl[0].shape.coordinates[Math.floor(srv_fl[0].shape.coordinates.length / 2)][0];
    var newLat = srv_fl[0].shape.coordinates[Math.floor(srv_fl[0].shape.coordinates.length / 2)][1];
    comid = srv_fl[0].comid.toString();
    $('#longInput').val(newLon);
    $('#latInput').val(newLat);
    $('#comidInput').val(comid);

    var element = document.getElementById('popup');
    lonlat = ol.proj.transform([newLon, newLat], 'EPSG:4326', 'EPSG:3857');
    map.getOverlays().item(0).setPosition(lonlat);
    var displayContent = "<p>COMID: " + comid + "</p>";
    $(element).popover({
                    'placement': 'top',
                    'html': true,
                    'content': displayContent
                });

                $(element).popover('show');
                $(element).next().css('cursor', 'text');

    //add the selected flow line to the map
    for (var i in srv_fl) {
        selected_streams_layer.getSource().clear();
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
        selected_streams_layer.getSource().clear();
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
        url: 'get-netcdf-data/',
        dataType: 'json',
        data: {
            'config': config,
            'geom': geom,
            'variable': variable,
            'COMID': comid,
            'startDate': date,
            'time': time,
            'lag': lag.toString(),
            'endDate': endDate
        },
        error: function (jqXHR, textStatus, errorThrown) {
            $('#info').html('<p class="alert alert-danger" style="text-align: center"><strong>An unknown error occurred while retrieving the data</strong></p>');
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
                if ("ts_pairs_data" in data)
                {
                    var returned_tsPairsData = JSON.parse(data.ts_pairs_data);
                    console.log(returned_tsPairsData);
                    for (var key in returned_tsPairsData)
                    {
                        if (returned_tsPairsData[key][2] === 'notLong')
                        {
                            var d = new Date(0);
                            startDate = d.setUTCSeconds(returned_tsPairsData[key][0]);
                            seriesData = returned_tsPairsData[key][1];
                            nc_chart.yAxis[0].setExtremes(null, null);
                            plotData(config, geom, variable, seriesData, startDate);
                        }
                        else
                        {
                            for (j = 0; j < returned_tsPairsData[key].length; j++)
                            {
                                var d = new Date(0);
                                var startDateG = d.setUTCSeconds(returned_tsPairsData[key][j][0]);
                                for (i = 1; i < returned_tsPairsData[key][j].length - 1; i++)
                                {
                                    var seriesDataTemp = returned_tsPairsData[key][j][i];
                                    var seriesDesc = 'Member 0' + String(i) + ' ' +
                                        returned_tsPairsData[key][j][returned_tsPairsData[key][j].length - 1];
                                    seriesDataGroup.push([seriesDataTemp, seriesDesc, startDateG]);
                                    nc_chart.yAxis[0].setExtremes(null, null);
                                    plotData(config, geom, variable, seriesDataTemp, startDateG, i - 1, seriesDesc);
                                }
                            } // for (j = 0;
                        } // else
                    } //for (var key i
                } //if ("ts_pairs_data" in data)
            } else if ("error" in data) {
                $('#nc-chart').addClass('hidden');
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
                title: {text: 'Time (UTC)'},
                minRange: 3600000,
                startDate: startDate
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
        var default_chart_settings = {
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
                minRange: 14 * 3600000,
                min: startDate
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

var plotData = function(config, geom, variable, data, start, colorIndex, seriesDesc)
{
    if (config !== 'long_range')
    {
        $('#actionBtns').removeClass('hidden');
    }

    var calib = calibrateModel(config, geom, start);

    if (variable === 'streamflow' || variable === 'inflow' || variable === 'outflow')
    {
        var units = 'Flow (cfs)';
    }
    else if (variable === 'velocity')
    {
        var units = 'Velocity (ft/s)';
        nc_chart.yAxis[0].setTitle({text: units});
        $('tspan:contains("Change Units")').parent().parent().attr('hidden', true);
    }
    else if (variable === 'SNOWH')
    {
        var units = 'Snow Depth (Feet)';
        nc_chart.yAxis[0].setTitle({text: units});
        $('tspan:contains("Change Units")').parent().parent().attr('hidden', true);
    }
    else if (variable === 'SNEQV')
    {
        var units = 'Snow Water Equivalent (Feet)';
        nc_chart.yAxis[0].setTitle({text: units});
        $('tspan:contains("Change Units")').parent().parent().attr('hidden', true);
    }
    else if (variable === 'ACCET' || variable === 'ACCECAN' || variable === 'CANWAT' ||
        variable === 'UGDRNOFF' || variable === 'SFCRNOFF')
    {
        var units = 'Depth (Inches)';
        nc_chart.yAxis[0].setTitle({text: units});
        $('tspan:contains("Change Units")').parent().parent().attr('hidden', true);
    }
    else if (variable === 'FSNO')
    {
        var units = 'Snow Cover (Fraction)';
        nc_chart.yAxis[0].setTitle({text: units});
        $('tspan:contains("Change Units")').parent().parent().attr('hidden', true);
    }
    else if (variable === 'SOIL_M')
    {
        var units = 'Soil Moisture';
        nc_chart.yAxis[0].setTitle({text: units});
        $('tspan:contains("Change Units")').parent().parent().attr('hidden', true);
    }
    else if (variable === 'SOILSAT_TOP' || variable === 'SOILSAT')
    {
        var units = 'Soil Saturation (Fraction)';
        nc_chart.yAxis[0].setTitle({text: units});
        $('tspan:contains("Change Units")').parent().parent().attr('hidden', true);
    }
    else if (variable === 'SNOWT_AVG' || variable === 'SOIL_T')
    {
        var units = 'Temperature (Kelvin)';
        nc_chart.yAxis[0].setTitle({text: units});
        $('tspan:contains("Change Units")').parent().parent().attr('hidden', true);
    }
    else if (variable === 'RAINRATE')
    {
        var units = 'Surface Precipitation Rate (mm/s)';
        nc_chart.yAxis[0].setTitle({text: units});
        $('tspan:contains("Change Units")').parent().parent().attr('hidden', true);
    }

    if (config !== 'long_range')
    {
        var data_series =
        {
            type: 'area',
            name: units,
            data: data,
            pointStart: calib['start'],
            pointInterval: calib['interval']
        };
        nc_chart.addSeries(data_series);
        if ($('#nc-chart').hasClass('hidden'))
        {
            $('#nc-chart').removeClass('hidden');
            $(window).resize();
        }
    }
    else
    {
        var data_series =
        {
            type: 'area',
            color: Highcharts.getOptions().colors[colorIndex],
            fillOpacity: 0.3,
            name: seriesDesc + ' ' + units,
            data: data,
            pointStart: start,
            pointInterval: calib['interval']
        };
        nc_chart.addSeries(data_series);
        if ($('#nc-chart').hasClass('hidden'))
        {
            $('#nc-chart').removeClass('hidden');
            $(window).resize();
        }
    } // else
}; //var plotData = function

function clearErrorSelection() {
    var numFeatures = selected_streams_layer.getSource().getFeatures().length;
    var lastFeature = selected_streams_layer.getSource().getFeatures()[numFeatures-1];
    selected_streams_layer.getSource().removeFeature(lastFeature);
}

function changeUnits(config) {
    if (config !== 'long_range') {
        var calib = calibrateModel(config, geom, startDate);
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
                var calib = calibrateModel(config, geom);
                var data_series = {
                    type: 'area',
                    name: seriesDataGroup[i][1] + ' Flow (cms)',
                    data: newSeries,
                    pointStart: seriesDataGroup[i][2],
                    pointInterval: calib['interval']
                };
                nc_chart.addSeries(data_series);
            }
        }
        else
        {
            while(nc_chart.series.length > 0)
            {
                nc_chart.series[0].remove(true);
            }
            nc_chart.yAxis[0].setTitle({text: 'Flow (cfs)'});

            for (i = 0; i < seriesDataGroup.length; i++)
            {
                var calib = calibrateModel(config, geom);
                var data_series = {
                    type: 'area',
                    name: seriesDataGroup[i][1] + ' Flow (cfs)',
                    data: seriesDataGroup[i][0],
                    pointStart: seriesDataGroup[i][2],
                    pointInterval: calib['interval']
                };
                nc_chart.addSeries(data_series);
            }
        }
    }
}

function calibrateModel(config, geom, date) {
    var interval;
    var start = date;
    if (config === 'short_range') {
        interval = 3600 * 1000; // one hour
    } else if (config === 'analysis_assim') {
        interval = 3600 * 1000; // one hour
    } else if (config === 'medium_range') {
        interval = 3600 * 1000 * 3; // three hours
    } else {
        if (geom != 'land')
        {
            interval = 3600 * 1000 * 6; // six hours
        }
        else
        {
            interval = 3600 * 1000 * 24; // 24 hours
        }
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
                resTableHtml = '<table id="tbl-watersheds"><thead><th></th><th>Title</th><th>File</th><th>Owner</th></thead><tbody>';

            if (response.hasOwnProperty('success')) {
                if (response.hasOwnProperty('resources')) {
                    resources = JSON.parse(response.resources);
                    if (resources.length === 0) {
                        $popupLoadWatershed.find('.modal-body').html('<b>It appears that you do not own any HydroShare resource that can be imported as watershed.</b>');
                    }
                    else
                    {
                        resources.forEach(function (resource) {
                            resTableHtml += '<tr>' +
                                '<td><input type="radio" name="resource" class="rdo-res" data-filename="' + resource.filename + '" value="' + resource.id + '"></td>' +
                                '<td class="res_title">' + resource.title + '</td>' +
                                '<td class="res_owner">' + resource.filename + '</td>' +
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
            if (watershed.hasOwnProperty('success'))
            {
                addGeojsonLayerToMap(watershed.geojson_str, watershed.id, true);
                $popupLoadWatershed.modal('hide');
            }
            else
            {
                alert(watershed.error);
            }
            $btnLoadWatershed.prop('disabled', false);
        }
    });
}

function addGeojsonLayerToMap(geojsonStr, watershedId, zoomTo)
{
    geojsonStr = geojsonStr.replace(/&quot;/g, '"'); // Unencode the encoded double-quotes

    var geoJson = JSON.parse(geojsonStr);
    watershedLayer.getSource().clear();

    // this geojson obj is the "Geometry" part (Polygon) of a geojson, not FeatureCollection or others
    var geometry = new ol.format.GeoJSON().readGeometry(geoJson);
    var fea = new ol.Feature(geometry);
    watershedLayer.getSource().addFeature(fea);

    if (zoomTo)
    {
        mapView.fit(watershedLayer.getSource().getExtent(), map.getSize());
    }
    $('#input-watershed-id').val(watershedId);
}

//https://davidwalsh.name/query-string-javascript
function getUrlParameter(name, url)
{
    name = name.replace(/[\[]/, '\\[').replace(/[\]]/, '\\]');
    var regex = new RegExp('[\\?&]' + name + '=([^&#]*)');
    if (url === null)
    {
        var results = regex.exec(location.search);
    }
    else
    {
        var results = regex.exec(url);
    }

    return results === null ? '' : decodeURIComponent(results[1].replace(/\+/g, ' '));
}

$("#subsetBtn").on("click", function(){
    var watershed_fea_list = watershedLayer.getSource().getFeatures();
    if (watershed_fea_list.length == 0)
    {
        alert("no watershed loaded");
        return;
    }
    $("#subsetBtn, #watershedBtn, #submitBtn").attr('disabled','disabled');

    subset_watershed();
});

function subset_watershed()
{

    var watershed_fea_list = watershedLayer.getSource().getFeatures();
    if (watershed_fea_list.length == 0)
    {
        alert("no watershed loaded");
        return;
    }
    var watershed_fea = watershed_fea_list[0];
    if (watershed_fea.getGeometry().getType().toLowerCase() != "polygon")
    {
        alert("not a polygon");
    }
    var geoJSON = new ol.format.GeoJSON();
    var geom_json = geoJSON.writeGeometry(watershed_fea.getGeometry());

    url = $('#paramForm').serialize();
    // function getUrlParameter() requires a valid url: http + domain + query string
    // make a fake url
    url = "http://www.hydroshare.org/?" + url;
    var parameter = {
        config: getUrlParameter("config", url),
        geom: getUrlParameter("geom", url),
        variable: getUrlParameter("variable", url),
        startDate: getUrlParameter("startDate", url),
        endDate: getUrlParameter("endDate", url),
        time: getUrlParameter("time", url),
        lag_00z: getUrlParameter("00z", url),
        lag_06z: getUrlParameter("06z", url),
        lag_12z: getUrlParameter("12z", url),
        lag_18z: getUrlParameter("18z",url)
    };


    var data = {geometry: geom_json, parameter: parameter};

    //http://stackoverflow.com/questions/28165424/download-file-via-jquery-ajax-post
    // Use XMLHttpRequest instead of Jquery $ajax
    xhttp = new XMLHttpRequest();
    xhttp.onreadystatechange = function() {
        var a;
        if (xhttp.readyState === 4 && xhttp.status === 200)
        {
            // Trick for making downloadable link
            a = document.createElement('a');
            a.href = window.URL.createObjectURL(xhttp.response);
            // Give filename you wish to download
            a.download = "NWM_subset.zip";
            a.style.display = 'none';
            document.body.appendChild(a);
            a.click();
            $("#subsetBtn, #watershedBtn, #submitBtn").removeAttr('disabled');
        }
        else if  (xhttp.status != 200 && xhttp.status != 0)
        {
            xhttp.abort();
            alert("Failed to subset this watershed");
            $("#subsetBtn, #watershedBtn, #submitBtn").removeAttr('disabled');
        }

    }; //xhttp.onreadystatechange
    // Post data to URL which handles post request
    xhttp.open("POST", 'subset-watershed/');
    xhttp.setRequestHeader("Content-Type", "application/json");
    // You should set responseType as blob for binary responses
    xhttp.responseType = 'blob';
    xhttp.send(JSON.stringify(data));
}