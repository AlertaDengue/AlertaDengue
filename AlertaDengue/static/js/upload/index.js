var uploadStatus = {};

$(document).ready(function() {

  function is_ready() {
    for (var card_id in uploadStatus) {
      if (uploadStatus[card_id].status !== "done") {
        return false;
      }
    }
    return true;
  }

  window.addEventListener("beforeunload", function(e) {
    if (is_ready()) {
      return undefined;
    }

    var confirmationMessage = 'Existem alterações no formulário. Se você sair agora '
      + 'todas as alterações serão perdidas.';

    (e || window.event).returnValue = confirmationMessage;
    return confirmationMessage;
  });
});


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
      overlay.style.display = 'flex';
      overlay.style.flexDirection = 'column';
      overlay.style.alignItems = 'center';
      overlay.style.justifyContent = 'center';
      overlay.innerHTML = `
        <i class="fas fa-2x fa-sync-alt fa-spin"></i>
        <div class="progress" style="margin-top: 8px; font-size: 14px; align-items: center;">0%</div>`;
      card.querySelector('.card').appendChild(overlay);

      const progress = overlay.querySelector('.progress');

      function onload(e) {
        try {
          spark.append(e.target.result);
          current_chunk++;
          progress.textContent = `${Math.min((current_chunk / total_chunks) * 100, 100).toFixed(2)}%`;
          if (current_chunk < total_chunks) {
            read_next_chunk();
          } else {
            const md5 = spark.end();
            data.md5 = md5;
            resolve(md5);
          }
        } catch (error) {
          card_error(card, error);
          reject(error);
        }
      }

      function read_next_chunk() {
        var reader = new FileReader();
        var start = current_chunk * chunk_size;
        var end = Math.min(start + chunk_size, file.size);
        reader.onload = onload;
        reader.onerror = function(error) {
          card_error(card, error);
          reject(error);
        };
        reader.readAsArrayBuffer(slice.call(file, start, end));
      }

      read_next_chunk();

    } catch (error) {
      card_error(card, error);
      reject(error);
    }
  });
}


function card_error(card, errorMessage) {
  const $card = window.jQuery && card instanceof jQuery ? card : $(card);

  const $cardEl = $card.find('.card');
  $cardEl.removeClass('card-secondary').addClass('card-danger');

  const $overlay = $cardEl.find('.overlay');
  if ($overlay.length) {
    $overlay.html(`
      <i class="fas fa-2x fa-times" 
         style="cursor: pointer; position: relative;" 
         data-tooltip="${errorMessage}"></i>
    `);

    $overlay.find('i').on('click', function() {
      $card.remove();
    });
  }
}


function delete_chunked_upload(upload_id) {
  $.ajax({
    type: "DELETE",
    url: `chunked/${upload_id}/delete/`,
    headers: { 'X-CSRFToken': csrf },
    success: function() {
      console.log(`delete success: ${upload_id}`);
    },
    error: function(jqXHR, textStatus, errorThrown) {
      console.error("delete error", errorThrown);
    }
  });
}

function upload_card(card_id, action, filename, formData) {
  return new Promise((resolve, reject) => {
    if (action === "get") {
      $.ajax({
        url: `file-card/?filename=${encodeURIComponent(filename)}`,
        method: "GET",
        headers: {
          "X-Requested-With": "XMLHttpRequest"
        },
        success: function(response) {
          const card = $('<div>', { id: card_id });
          card.html(response);
          $('#upload-files').append(card);

          const closeButton = card.find('.close-button');
          closeButton.on('click', function() {
            card.remove();
          });

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

function delete_card(card_id, upload_id) {
  if (upload_id) {
    delete_chunked_upload(data.result.upload_id);
  }
  delete uploadStatus[card_id];
  $(`#${card_id}`).remove();

}

function chunked_upload(element_id) {
  const id_parts = element_id.split('_').map((part, index) => (index === 1 ? parseInt(part) : part));
  const input_id = element_id.replace('#', '');
  const upload_id = [id_parts[0], `${id_parts[1] + 1}`].join('_');
  const card_id = `card_${id_parts[1]}`;

  if (!$('#upload-icon label').length) {
    $('#upload-files').prepend(`
      <div id="upload-icon">
        <label for="${input_id}" style="cursor: pointer; display: inline-block;">
          <i class="fa fa-plus-circle" style="font-size: 50px; color: #28a745;"></i>
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
      uploadStatus[card_id] = { "status": "pending" };
      chunked_upload(upload_id);

      upload_card(card_id, "get", data.files[0].name).then(card => {
        return calculate_md5(data, card);
      }).then(() => {
        $(`#${card_id} .card`).removeClass('card-secondary');
        $(`#${card_id} .card`).addClass('card-primary');
        data.formData = [
          { name: "csrfmiddlewaretoken", value: csrf },
          { name: "md5", value: data.md5 }
        ];
        data.submit();
        $(`#${card_id} .overlay`).remove();
      }).catch(error => {
        console.error('upload_card error: ', error);
      });
    },

    chunkdone: function(e, data) {
      console.log("chunkdone");
      if (!data.formData.find(f => f.name === "upload_id")) {
        data.formData.push({ name: "upload_id", value: data.result.upload_id });
      }
      $(`#${card_id} .close-button`).off('click').on('click', function() {
        delete_card(card_id, data.result.upload_id);
      });
    },

    done: function(e, data) {
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
          uploadStatus[card_id]["status"] = "done";
          $(`#${card_id} .card`).removeClass('card-secondary');
          $(`#${card_id} .card`).addClass('card-success');
          $(`#${card_id} .close-button`).off('click').on('click', function() {
            delete_card(card_id, data.result.upload_id);
          });
        },
        error: function(jqXHR, textStatus, errorThrown) {
          console.error("done error", errorThrown);
          card_error($(`#${card_id}`), errorThrown);
          if (data.result && data.result.upload_id) {
            delete_chunked_upload(data.result.upload_id);
          }
          $(`#${card_id} .close-button`).off('click').on('click', function() {
            delete_card(card_id);
          });
        }
      });
    },

    fail: function(e, data) {
      $(`#${card_id} .close-button`).off('click').on('click', function() {
        delete_card(card_id);
      });
      if (data.result && data.result.upload_id) {
        delete_chunked_upload(data.result.upload_id);
      }
    },

    stop: function(e, data) {
      $(`#${card_id} .close-button`).off('click').on('click', function() {
        delete_card(card_id);
      });
      if (data.result && data.result.upload_id) {
        delete_chunked_upload(data.result.upload_id);
      }
    }
  });
}

chunked_upload("#upload_1");
