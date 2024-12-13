function calculate_md5(file) {
  return new Promise((resolve) => {
    var chunk_size = 10000000; // 10Mb
    var slice = File.prototype.slice || File.prototype.mozSlice || File.prototype.webkitSlice;
    var spark = new SparkMD5.ArrayBuffer();
    var chunks = Math.ceil(file.size / chunk_size);
    let current_chunk = 0;

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
      var reader = new FileReader();
      var start = current_chunk * chunk_size;
      var end = Math.min(start + chunk_size, file.size);
      reader.onload = onload;
      reader.readAsArrayBuffer(slice.call(file, start, end));
    }

    read_next_chunk();
  });
}


$("#chunked_upload").fileupload({
  url: 'chunked/',
  dataType: "json",
  maxChunkSize: 10000000,
  headers: { 'X-CSRFToken': csrf },
  multipart: true,

  add: function(e, data) {
    console.log("add");
    console.log(data);

    $.each(data.files, function(index, file) {
      calculate_md5(file).then(md5 => {
        console.log("md5");
        console.log(md5);
        var jqXHR = data.submit()
          .done(function(result, textStatus, jqXHR) {
            console.log("add done");
            console.log(result);
            console.log(textStatus);
            console.log(jqXHR);
          })
          .fail(function(jqXHR, textStatus, errorThrown) {
            console.log("add fail");
            console.log(jqXHR);
            console.log(textStatus);
            console.log(errorThrown);
          });
      });
    });
  },

  progress: function(e, data) {
    console.log("progress");
    console.log(data);
    if (e.lengthComputable) {
      var progress = Math.round((data.loaded / data.total) * 100);
      console.log("Uploading", data.files[0].name, progress + "%");
    }
  },

  chunkdone: function(e, data) {
    console.log("chunkdone");
    console.log(data);
    console.log(data.result.upload_id);
  },

  done: function(e, data) {
    $.ajax({
      type: "POST",
      url: 'chunked/complete/',
      data: {
        csrfmiddlewaretoken: csrf,
        upload_id: data.result.upload_id,
      },
      dataType: "json",
      success: function(response) {
        console.log("done success");
        console.log(response);
      },
      error: function(jqXHR, textStatus, errorThrown) {
        console.log("done error");
        console.log(jqXHR);
        console.log(textStatus);
        console.log(errorThrown);
      }
    });
  },

  fail: function(e, data) {
    console.log("fail");
    console.log(data);
  }
});
