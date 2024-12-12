var form_data = [{ "name": "csrfmiddlewaretoken", "value": csrf }];

async function calculate_md5(file) {
  const chunk_size = 10000000; // 10Mb
  const slice = File.prototype.slice || File.prototype.mozSlice || File.prototype.webkitSlice;
  const spark = new SparkMD5.ArrayBuffer();
  const chunks = Math.ceil(file.size / chunk_size);
  let current_chunk = 0;

  return new Promise((resolve) => {
    function onload(e) {
      spark.append(e.target.result);
      current_chunk++;
      if (current_chunk < chunks) {
        read_next_chunk();
      } else {
        resolve(spark.end());
      }
    }

    function read_next_chunk() {
      const reader = new FileReader();
      const start = current_chunk * chunk_size;
      const end = Math.min(start + chunk_size, file.size);
      reader.onload = onload;
      reader.readAsArrayBuffer(slice.call(file, start, end));
    }

    read_next_chunk();
  });
}

async function upload(data) {
  const file = data.files[0];
  console.log(file);
  const md5 = await calculate_md5(file);
  console.log(md5);
}

$("#chunked_upload").fileupload({
  url: 'chunked/',
  dataType: "json",
  maxChunkSize: 10000000,
  formData: form_data,

  add: function(e, data) {
    upload(data);
    // $("#messages").empty();
    // form_data.splice(1);
    // calculate_md5(data.files[0], 10000000);
    // data.submit();
  },

  chunkdone: function(e, data) {
    console.log("chunkdone")
    console.log(data);
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
