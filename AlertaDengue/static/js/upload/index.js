function calculate_md5(data) {
  return new Promise((resolve) => {
    const file = data.files[0];
    var chunk_size = 10000000; // 10Mb
    var slice = File.prototype.slice || File.prototype.mozSlice || File.prototype.webkitSlice;
    var spark = new SparkMD5.ArrayBuffer();
    var total_chunks = Math.ceil(file.size / chunk_size);
    let current_chunk = 0;

    function onload(e) {
      spark.append(e.target.result);
      current_chunk++;
      if (current_chunk < total_chunks) {
        read_next_chunk();
      } else {
        const md5 = spark.end();
        data.md5 = md5;
        resolve(md5);
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

function delete_chunked_upload(upload_id) {
  $.ajax({
    type: "DELETE",
    url: `chunked/${upload_id}/delete/`,
    headers: { 'X-CSRFToken': csrf },
    success: function(response) {
      console.log("delete success");
    },
    error: function(jqXHR, textStatus, errorThrown) {
      console.log("delete error");
      console.log(jqXHR);
      console.log(errorThrown);
    }
  });
}

function upload_card(element_id, action, filename, formData) {
  if (action === "get") {
    $.ajax({
      url: `file-card/?filename=${encodeURIComponent(filename)}`,
      method: "GET",
      headers: {
        "X-Requested-With": "XMLHttpRequest"
      },
      success: function(response) {
        const card = $('<div>', { id: element_id });
        card.html(response);
        $('#upload-files').append(card);
      },
      error: function(xhr) {
        console.error("upload_card GET error");
      }
    });
  } else if (action === "post") {
    $.ajax({
      url: "file-card/",
      method: "POST",
      data: formData,
      processData: false,
      contentType: false,
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": csrf
      },
      success: function(response) {
        console.log("upload_card POST success");
      },
      error: function(xhr) {
        console.error("upload_card POST error");
      }
    });
  }
}

function chunked_upload(element_id) {
  const id_parts = element_id.split('_').map((part, index) => index === 1 ? parseInt(part) : part);

  if ($(element_id).length === 0) {
    $('#upload-files').append(`
      <label for="${element_id.replace('#', '')}" style="cursor: pointer; display: inline-block;" alt="Upload file">
        <i class="fa fa-plus-circle" style="font-size: 50px; color: #2ff96c;"></i>
      </label>
      <input
        id="${element_id.replace('#', '')}"
        type="file"
        name="file"
        accept=".csv,.dbf,.parquet,.csv.gz,.csv.zip,.dbf.gz,.dbf.zip,.parquet.gz,.parquet.zip"
      >
    `);
  }

  $(element_id).fileupload({
    url: 'chunked/',
    dataType: "json",
    maxChunkSize: 10000000,
    headers: { 'X-CSRFToken': csrf },

    add: function(e, data) {
      $(`label[for="${element_id.replace('#', '')}"]`).hide();
      chunked_upload([id_parts[0], `${id_parts[1] + 1}`].join('_'));
      upload_card("card_1", "get", data.files[0].name);

      calculate_md5(data).then(() => {
        data.formData = [
          { name: "csrfmiddlewaretoken", value: csrf },
          { name: "md5", value: data.md5 }
        ];
        data.submit();
      });
    },

    chunkdone: function(e, data) {
      console.log("chunkdone");
      if (!data.formData.find(f => f.name === "upload_id")) {
        data.formData.push({ name: "upload_id", value: data.result.upload_id });
      }
      var progress = parseInt(data.loaded / data.total * 100.0, 10);
    },

    done: function(e, data) {
      console.log("done")
      console.log(data.result.upload_id);
      $.ajax({
        type: "POST",
        url: 'chunked/complete/',
        data: {
          csrfmiddlewaretoken: csrf,
          upload_id: data.result.upload_id,
          md5: data.md5,
        },
        dataType: "json",
        success: function(response) {
          console.log("done success");
          console.log(response);
        },
        error: function(jqXHR, textStatus, errorThrown) {
          console.log("done error");
          if (data.result && data.result.upload_id) {
            delete_chunked_upload(data.result.upload_id);
          }
        }
      });
    },

    fail: function(e, data) {
      if (data.result && data.result.upload_id) {
        delete_chunked_upload(data.result.upload_id);
      }
    },

    stop: function(e, data) {
      if (data.result && data.result.upload_id) {
        delete_chunked_upload(data.result.upload_id);
      }
    }
  });
}

chunked_upload("#upload_1");
