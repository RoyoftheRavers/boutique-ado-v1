// Shows the chosen file's name below the custom upload button, since the
// real file input is invisible (see base.css) and gives no feedback of
// its own on selection.
$(document).on('change', '.custom-file-upload-btn input[type="file"]', function () {
    var files = this.files;
    var fileName = files.length ? files[0].name : '';
    $(this).closest('.custom-file-upload-btn').next('.custom-file-filename').text(fileName);
});
