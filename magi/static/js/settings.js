
$(document).ready(function() {
    // Delete links
    $('a[href=#deleteLink]').click(function(e) {
	    e.preventDefault();
	    var link = $(this).closest('tr');
	    $.get('/ajax/deletelink/' + $(this).attr('data-link-id'), function(data) {
	        link.remove();
	    });
	    return false;
    });
    // Format hide tags form
    d_FieldCheckBoxes($('[id^="id_d_hidden_tags-"]'));
});
