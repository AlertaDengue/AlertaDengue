var md5 = ""
var form_data = [{ "name": "csrfmiddlewaretoken", "value": csrf }];
var uploadCompleted = false;

function update_progress_bar(progress) {
  $(".progress").show();
  $(".progress-bar").attr("style", "width: " + progress + "%");
  $(".progress-bar").attr("aria-value-now", progress);
  $(".progress-bar>span").text(progress + "%");
}

function calculate_md5(file, chunk_size) {
  const slice = File.prototype.slice || File.prototype.mozSlice || File.prototype.webkitSlice;
  const spark = new SparkMD5.ArrayBuffer();
  const chunks = Math.ceil(file.size / chunk_size);
  let current_chunk = 0;

  function onload(e) {
    spark.append(e.target.result);
    current_chunk++;
    if (current_chunk < chunks) {
      read_next_chunk();
    } else {
      md5 = spark.end();
    }
  };

  function read_next_chunk() {
    const reader = new FileReader();
    const start = current_chunk * chunk_size;
    const end = Math.min(start + chunk_size, file.size);
    reader.onload = onload;
    reader.readAsArrayBuffer(slice.call(file, start, end));
  };

  read_next_chunk();
}

$("#chunked_upload").fileupload({
  url: 'chunked/',
  dataType: "json",
  maxChunkSize: 10000000,
  formData: form_data,

  add: function(e, data) {
    $("#messages").empty();
    form_data.splice(1);
    calculate_md5(data.files[0], 10000000);
    data.submit();
    $("#filename_display").show();
    $("#filename_display>span").text("Enviando " + data.files[0].name + "...");
    $("form>.alert").hide();
    window.form_has_changed = true;
    uploadCompleted = false;
  },

  chunkdone: function(e, data) {
    var progress = parseInt(data.loaded / data.total * 100.0, 10);
    update_progress_bar(progress);
  },

  done: function(e, data) {
    $.ajax({
      type: "POST",
      url: 'chunked/complete/',
      data: {
        csrfmiddlewaretoken: csrf,
        upload_id: data.result.upload_id,
        md5: md5
      },
      dataType: "json",

      success: function(file) {
        uploadCompleted = true;
        update_progress_bar(100);
        $("#filename_display>span").html(
          file.filename +
          " pronto para ser enviado. <br />Preencha os dados abaixo e clique em 'Enviar' para importar os dados."
        );
        $("#submit_button").prop("disabled", false);

        if ($("#upload_id").length > 0) {
          $("#upload_id").val(file.id);
        } else {
          $("<input>", {
            type: "hidden",
            id: "upload_id",
            name: "upload_id",
            value: file.id
          }).appendTo("form");
        }

        if ($("#filename").length > 0) {
          $("#filename").val(file.filename);
        } else {
          $("<input>", {
            type: "hidden",
            id: "filename",
            name: "filename",
            value: file.filename
          }).appendTo("form");
        }
      },

      error: function(jqXHR, textStatus, errorThrown) {
        console.log(jqXHR);
        console.log(textStatus);
        console.log(errorThrown);
      }
    });
  },
});
