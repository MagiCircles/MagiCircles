
$(document).ready(function() {
    $('#id_birthdate, #id_show_birthdate_year').closest('.form-group').hide();
    $('#id_password').focus(function(e) {
        $('#id_birthdate, #id_show_birthdate_year').closest('.form-group').show('slow');
    });
});
