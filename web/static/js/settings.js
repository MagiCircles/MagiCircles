
$(document).ready(function() {
    multiCuteForms({'language': true, 'color': true});

    $('a[href=#deleteLink]').click(function(e) {
	e.preventDefault();
	var link = $(this).closest('tr');
	$.get('/ajax/deletelink/' + $(this).attr('data-link-id'), function(data) {
	    link.remove();
	});
	return false;
    });
});
