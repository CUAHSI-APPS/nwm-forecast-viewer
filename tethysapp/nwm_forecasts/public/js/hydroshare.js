var resource_url

$(function(){
    $("input[name='time_period']").click(function () {
        if( $(this).val() == 'preceding' ) {
            $("#time_selection").show();
        }
        else {
            $("#time_selection").hide();
        }
    });
});

$('#HSbtn').on('click', function () {
    var id = $("#comidInput").val();
    var config = $("#config").val();
    var variable = $("#variable").val();
    var lat = $("#latInput").val();
    var long = $("#longInput").val();

    var resTitle = 'nwm ' + config.replace('_', ' ') + ' ' + variable + ' for id ' + id;
    var resAbstr = 'This resource contains a WaterML file retrieved from the NWM Forecast Viewer App with forecast data for the ' + config.replace('_', ' ') + ' configuration of the NWM at location Lat: ' + lat + '; Long: ' + long;
    var resKwds ='NWM';

    $("#resource-title").val(resTitle);
    $("#resource-abstract").val(resAbstr);
    $("#resource-keywords").val(resKwds);
    $('#display-status').html('');
    resource_url = $("#WMLbtn").attr("href");
});

$('#hydroshare-proceed').on('click', function ()  {
    if ($("#time_selection").length > 0) {
        if ($("input[name='time_period']:checked").val() == 'preceding') {
            var period = $("input[name='period']").val();
            var units = $('#time_period_units').val();
            var span = period + '-' + units;
            resource_url = "/apps/gaugeviewwml/waterml/?type=usgsiv&gaugeid=" + id + "&span=" + span;
    };

    //now we construct the WaterML..
    var waterml_link = resource_url;
    var upload_link = '/apps/gaugeviewwml/upload-to-hydroshare/';

    $('#display-status').removeClass('error');
    $('#display-status').addClass('uploading');
    $('#display-status').html('<em>Uploading...</em>');

    var resourceAbstract = $('#resource-abstract').val();
    var resourceTitle = $('#resource-title').val();
    var resourceKeywords = $('#resource-keywords').val() ? $('#resource-keywords').val() : "";
    var resourcePublic = $("#resource-public").prop("checked");

    if (!resourceTitle || !resourceKeywords || !resourceAbstract)
    {
        $('#display-status').removeClass('uploading');
        $('#display-status').addClass('error');
        $('#display-status').html('<em>You must provide all metadata information.</em>');
        return
    }

    var csrf_token = getCookie('csrftoken');
    $(this).prop('disabled', true);
    $.ajax({
        type: 'POST',
        url: upload_link,
        headers:{'X-CSRFToken':csrf_token},
        dataType:'json',
        data: {'title':resourceTitle, 'abstract': resourceAbstract,
            'keyword': resourceKeywords, 'waterml_link': waterml_link, 'public': resourcePublic},
        success: function (data) {
            $('#hydroshare-proceed').prop('disabled', false);
            if ('error' in data) {
                $('#display-status').removeClass('uploading');
                $('#display-status').addClass('error');
                $('#display-status').html('<em>' + data.error + '</em>');
            }
            else
            {
                $('#display-status').removeClass('uploading');
                $('#display-status').addClass('success');
                $('#display-status').html('<em>' + data.success + ' View in HydroShare <a href="https://www.hydroshare.org/resource/' + data.newResource +
                    '" target="_blank">HERE</a></em>');
            }
        },
        error: function (jqXHR, textStatus, errorThrown) {
            $('#hydroshare-proceed').prop('disabled', false);
            $('#display-status').removeClass('uploading');
            $('#display-status').addClass('error');
            $('#display-status').html('<em>' + errorThrown + '</em>');
        }
    });
});

function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie != '') {
        var cookies = document.cookie.split(';');
        for (var i = 0; i < cookies.length; i++) {
            var cookie = jQuery.trim(cookies[i]);
            // Does this cookie string begin with the name we want?
            if (cookie.substring(0, name.length + 1) == (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}