// Show bootstrap alert
function showAlert(message, type) {
    console.log('alert ' + type + ': ' + message)
    var wrapper = document.createElement('div')
    wrapper.innerHTML = '<div class="alert alert-' + type + ' alert-dismissible" role="alert">' + message + '<button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button></div>'
    document.getElementById('alerts-placeholder').append(wrapper)
}

function invokeFatmanAction(actionName, endpoint, that, csrf_token) {
    var fatman_name = that.attr('fatman-name');
    var fatman_version = that.attr('fatman-version');
    var actionPrefix = actionName + ' ' + fatman_name + ' v' + fatman_version
    console.log(actionPrefix + '...');
    var previousHtml = that.html();
    that.prop("disabled", true);
    that.html(
        `<div class="spinner-border" role="status"><span class="visually-hidden">Loading...</span></div>`
    );
    $.ajax({
        url: '/dashboard/api/' + endpoint + '/' + fatman_name + '/' + fatman_version,
        type: 'post',
        data: {
            csrfmiddlewaretoken: csrf_token
        },
        cache: false,
        success: function(data) {
            that.prop("disabled", false);
            that.html(previousHtml);
            var message = 'Success: ' + actionPrefix;
            showAlert(message, 'success');
        },
        error: function (xhr, status, error) {
            if (xhr.hasOwnProperty('responseJSON') && xhr.responseJSON.hasOwnProperty('error')) { 
                message = xhr.responseJSON.error;
            } else {
                message = xhr.statusText;
            }
            that.prop("disabled", false);
            that.html(previousHtml);
            showAlert('Error: ' + actionPrefix + ': ' + message, 'danger');
        }
    });
}

function showModal(title, body, onConfirm) {
    var modal = new bootstrap.Modal(document.getElementById('modalTemplate'), {})
    document.getElementById('modalTemplateTitle').innerHTML = title
    document.getElementById('modalTemplateBody').innerHTML = body
    modal.show()
    $("#modalTemplateConfirmButton").prop("onclick", null).off("click")
    $("#modalTemplateConfirmButton").click(function () {
        modal.hide()
        onConfirm()
    })
}
