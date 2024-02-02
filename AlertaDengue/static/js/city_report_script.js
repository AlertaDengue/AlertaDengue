// city_report_script.js
function openReport() {
    var geocode = $('#geocode option:selected').val();
    var epidate = $('#epidate').val();
    var url = '/api/epi_year_week?epidate=' + epidate;
  
    $.ajax({
        dataType: 'json',
        url: url,
        success: function(data) {
          window.location.href = '/report/{{ state }}/' + geocode + '/' + data['epi_year_week'];
        }
    });
  
    return false;
  }
  