
function updateReport() {
    // Moderation reports buttons
    $('.well.report form').unbind('submit');
    $('.well.report form').submit(function(e) {
	e.preventDefault();
	var button = $(this).find('input[type="submit"]');
	button.prop('value', gettext('Loading'));
	disableButton(button);
	$(this).ajaxSubmit({
	    context: this,
	    success: function(data) {
		data['moderated_reports'].forEach(function(id) {
		    $('.report[data-report-id="' + id + '"]').removeClass('report-Pending');
		    $('.report[data-report-id="' + id + '"]').addClass('report-' + data['action']);
		    $('.report[data-report-id="' + id + '"] .report_status').text(data['action']);
		    $('.report[data-report-id="' + id + '"] .staff-buttons').remove();
		    if (data['action'] == 'Deleted') {
			$('.report[data-report-id="' + id + '"] .open-thing').remove()
		    }
		});
	    },
	    error: genericAjaxError,
	});
	return false;
    });
    // Open activity button
    ajaxModals();
}
