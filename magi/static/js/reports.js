
function updateReport() {
    // Moderation reports buttons
    $('.well.report form').unbind('submit');
    $('.well.report form').submit(function(e) {
	e.preventDefault();
	var form = $(this);
	var report_id = form.closest('.report').data('report-id');
	var submitForm = function() {
	    var button = form.find('input[type="submit"]');
	    button.prop('value', gettext('Loading'));
	    disableButton(button);
	    form.ajaxSubmit({
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
	}
	if (form.attr('action').indexOf('Deleted') != '-1') {
	    $.get('/ajax/reportwhatwillbedeleted/' + report_id + '/', function(html) {
		confirmModal(function() {
		    submitForm();
		}, undefined, undefined, '<ul>' + form.find('ul').html() + '</ul>' + html);
	    });
	} else {
	    submitForm();
	}
	return false;
    });
    // Show/hide textarea for details
    $('[name="reason"]').change(function(e) {
	var value = $(this).val();
	var form = $(this).closest('form');
	var textarea = form.find('textarea[name="staff_message"]');
	if (value == '_other') {
	    textarea.val('');
	} else {
	    textarea.val(value);
	}
	if (value != '') {
	    textarea.show();
	} else {
	    textarea.hide();
	}
    });
}
