// report_type_script.js
function openReport() {
    var state_initial = $('#state option:selected').val();
    var report_type = $('#report-type option:selected').val();
    window.location.href = '/report/' + state_initial + '/' + report_type;
    return false;
  }
  