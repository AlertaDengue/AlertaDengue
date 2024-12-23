function calculate_md5(data, card) {
  return new Promise((resolve, reject) => {
    try {
      const file = data.files[0];
      var chunk_size = 10000000; // 10Mb
      var slice = File.prototype.slice || File.prototype.mozSlice || File.prototype.webkitSlice;
      var spark = new SparkMD5.ArrayBuffer();
      var total_chunks = Math.ceil(file.size / chunk_size);
      let current_chunk = 0;

      const overlay = document.createElement('div');
      overlay.className = 'overlay';
      overlay.innerHTML = '<i class="fas fa-2x fa-sync-alt fa-spin"></i>';
      card.querySelector('.card').appendChild(overlay);

      function onload(e) {
        try {
          spark.append(e.target.result);
          current_chunk++;
          if (current_chunk < total_chunks) {
            read_next_chunk();
          } else {
            const md5 = spark.end();
            data.md5 = md5;
            card.removeChild(overlay);
            resolve(md5);
          }
        } catch (error) {
          cardError(card, overlay, 'Error processing chunk: ' + error);
          reject(error);
        }
      }

      function read_next_chunk() {
        var reader = new FileReader();
        var start = current_chunk * chunk_size;
        var end = Math.min(start + chunk_size, file.size);
        reader.onload = onload;
        reader.onerror = function(error) {
          cardError(card, overlay, 'Error reading file chunk: ' + error);
          reject(error);
        };
        reader.readAsArrayBuffer(slice.call(file, start, end));
      }

      read_next_chunk();

    } catch (error) {
      cardError(card, overlay, 'Error in calculate_md5 function: ' + error);
      reject(error);
    }
  });
}

function cardError(card, overlay, errorMessage) {
  const cardEl = card.querySelector('.card');
  cardEl.classList.remove('card-secondary');
  cardEl.classList.add('card-danger');

  overlay.innerHTML = `
    <i class="fas fa-2x fa-times" 
       style="cursor: pointer; position: relative;" 
       data-tooltip="${errorMessage}"></i>`;

  overlay.querySelector('i').addEventListener('click', () => {
    // cardEl.removeChild(overlay);
  });
}


function delete_chunked_upload(upload_id) {
  $.ajax({
    type: "DELETE",
    url: `chunked/${upload_id}/delete/`,
    headers: { 'X-CSRFToken': csrf },
    success: function() {
      console.log("delete success");
    },
    error: function(jqXHR, textStatus, errorThrown) {
      console.error("delete error", errorThrown);
    }
  });
}

function upload_card(element_id, action, filename, formData) {
  return new Promise((resolve, reject) => {
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
          resolve(card[0]);
        },
        error: function(xhr) {
          console.error("upload_card GET error");
          reject(xhr);
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
        success: function() {
          console.log("upload_card POST success");
          resolve();
        },
        error: function(xhr) {
          console.error("upload_card POST error");
          reject(xhr);
        }
      });
    }
  });
}

function chunked_upload(element_id) {
  const id_parts = element_id.split('_').map((part, index) => (index === 1 ? parseInt(part) : part));
  const input_id = element_id.replace('#', '');

  if (!$('#upload-icon label').length) {
    $('#upload-files').prepend(`
      <div id="upload-icon">
        <label for="${input_id}" style="cursor: pointer; display: inline-block;">
          <i class="fa fa-plus-circle" style="font-size: 50px; color: #2ff96c;"></i>
        </label>
        <input
          id="${input_id}"
          type="file"
          name="file"
          accept=".csv,.dbf,.parquet,.csv.gz,.csv.zip,.dbf.gz,.dbf.zip,.parquet.gz,.parquet.zip"
          style="display: none;"
        >
      </div>
    `);
  } else {
    $('#upload-icon label').attr('for', input_id);

    $('#upload-icon input').remove();
    $('#upload-icon').append(`
      <input
        id="${input_id}"
        type="file"
        name="file"
        accept=".csv,.dbf,.parquet,.csv.gz,.csv.zip,.dbf.gz,.dbf.zip,.parquet.gz,.parquet.zip"
        style="display: none;"
      >
    `);
  }

  $(element_id).fileupload({
    url: 'chunked/',
    dataType: "json",
    maxChunkSize: 10000000,
    headers: { 'X-CSRFToken': csrf },

    add: function(e, data) {
      const upload_id = [id_parts[0], `${id_parts[1] + 1}`].join('_');
      const card_id = `card_${id_parts[1]}`;
      chunked_upload(upload_id);

      upload_card(card_id, "get", data.files[0].name).then(card => {
        return calculate_md5(data, card);
      }).then(() => {
        data.formData = [
          { name: "csrfmiddlewaretoken", value: csrf },
          { name: "md5", value: data.md5 }
        ];
        data.submit();
      }).catch(error => {
        console.error('upload_card error: ', error);
      });
    },

    chunkdone: function(e, data) {
      console.log("chunkdone");
      if (!data.formData.find(f => f.name === "upload_id")) {
        data.formData.push({ name: "upload_id", value: data.result.upload_id });
      }
    },

    done: function(e, data) {
      console.log("done");
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
          console.log("done success", response);
        },
        error: function(jqXHR, textStatus, errorThrown) {
          console.error("done error", errorThrown);
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
