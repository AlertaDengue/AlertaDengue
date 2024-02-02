// report_script.js
function openReport() {
    var epidate = $('#epidate').val();
    var url = '/api/epi_year_week?epidate=' + epidate;
  
    $.ajax({
        dataType: 'json',
        url: url,
        success: function(data) {
          window.location.href = (
            '/report/{{state}}/' +
            data['epi_year_week']
          );
        }
    });
  
    return false;
  }
  