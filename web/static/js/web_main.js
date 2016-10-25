
// *****************************************
// *****************************************
// Always called

// *****************************************
// Auto load forms

function disableButton(button) {
    button.unbind('click');
    button.click(function(e) {
	e.preventDefault();
	return false;
    });
}

function formloaders() {
    $('button[data-form-loader=true]').click(function(e) {
	$(this).html('<i class="flaticon-loading"></i>');
	disableButton($(this));
    });
}

function loadPageScroll() {
    $('a.page-scroll').unbind('click');
    $('a.page-scroll').bind('click', function(event) {
	var $anchor = $(this);
	$('html, body').stop().animate({
	    scrollTop: $($anchor.attr('href')).offset().top
	}, 1500, 'easeInOutExpo');
	event.preventDefault();
    });
}

// *****************************************
// Change Unknown / Yes / No to cute form All / Only / None

function cuteFormNullBool() {
    $('select option[value="1"]').each(function() {
	var select = $(this).parent();
	var flag = true;
	select.find('option').each(function() {
	    if (!(($(this).attr('value') == '1' && $(this).text() == gettext('Unknown'))
		  || ($(this).attr('value') == '2' && $(this).text() == gettext('Yes'))
		  || ($(this).attr('value') == '3' && $(this).text() == gettext('No')))) {
		flag = false;
	    }
	});
	if (flag) {
	    cuteform(select, {
		'html': {
		    '1': gettext('All'),
		    '2': gettext('Only'),
		    '3': gettext('None'),
		},
	    });
	}
    });
}

// *****************************************
// Check if date input is supported and add an help text otherwise

function dateInputSupport() {
    var input = document.createElement('input');
    input.setAttribute('type','date');

    var notADateValue = 'not-a-date';
    input.setAttribute('value', notADateValue);

    if (!(input.value !== notADateValue)) {
	$('input[type="date"]').parent().find('.help-block').text('yyyy-mm-dd');
    }
}

// *****************************************
// Notifications

function notificationsHandler() {
    var button = $('a[href="/notifications/"]');
    var world = button.find('.flaticon-world');
    var loader = button.find('.flaticon-loading');
    var badge = button.find('.badge');
    if (badge.length > 0 && $(document).width() > 992) {
	var onClick = function(e) {
	    e.preventDefault();
	    button.unbind('click');
	    world.hide();
	    loader.show();
	    $.get('/ajax/notifications/?ajax_modal_only&page_size=2', function(data) {
		var onShown = function() {
		    var remaining = $('nav.navbar ul.navbar-right .popover span.remaining').text();
		    if (remaining != '') {
			badge.text(remaining);
			badge.show();
		    } else {
			button.unbind('click');
		    }
		};
		loader.hide();
		badge.hide();
		world.show();
		if ($('nav.navbar ul.navbar-right .popover').is(':visible')) {
		    $('nav.navbar ul.navbar-right .popover .popover-content').html(data);
		    onShown();
		} else {
		    button.popover({
			container: $('nav.navbar ul.navbar-right'),
			html: true,
			placement: 'bottom',
			content: data,
			trigger: 'manual',
		    });
		    button.popover('show');
		    button.on('shown.bs.popover', function () {
			onShown();
		    });
		}
	    });
	    return false;
	};
	button.click(onClick);
    }
}


function ajaxModals() {
    $('[data-ajax-url]').each(function() {
	var button = $(this);
	var modalButtons = 0;
	if (button.data('ajax-show-button') == true) {
	    modalButtons = undefined;
	}
	var button_content = button.html();
	button.unbind('click');
	button.click(function(e) {
	    var button_display = button.css('display');
	    if (button_display == 'inline') {
		button.css('display', 'inline-block');
	    }
	    var button_height = button.height();
	    var button_width = button.width();
	    button.html('<i class="flaticon-loading"></i>');
	    var loader = button.find('.flaticon-loading');
	    loader.height(button_height);
	    loader.width(button_width);
	    loader.css('line-height', button_height + 'px');
	    loader.css('font-size', (button_height - (button_height * 0.4)) + 'px');
	    $.get(button.data('ajax-url'), function(data) {
		button.css('display', button_display);
		button.html(button_content);
		var title = button.data('ajax-title');
		title = typeof title == 'undefined' ? button_content : title;
		modal_size = button.data('ajax-modal-size');
		freeModal(title, data, modalButtons, modal_size);
		if (typeof button.data('ajax-handle-form') != 'undefined') {
		    var ajaxModals_handleForms;
		    ajaxModals_handleForms = function() {
			formloaders();
			$('#freeModal form').submit(function(e) {
			    e.preventDefault();
			    var form_name = $(this).find('.generic-form-submit-button').attr('name');
			    $(this).ajaxSubmit({
				context: this,
				success: function(data) {
				    var form_modal_size = modal_size;
				    if (typeof form_name != 'undefined'
					&& $(data).find('form .generic-form-submit-button[name="' + form_name + '"]').length == 0
					&& $(data).find('form .errorlist').length == 0
					&& typeof button.data('ajax-modal-after-form-size') != 'undefined') {
					form_modal_size = button.data('ajax-modal-after-form-size');
				    }
				    freeModal(title, data, modalButtons, form_modal_size);
				    if (typeof form_name != 'undefined'
					&& $('#freeModal form .generic-form-submit-button[name="' + form_name + '"]').length > 0
					&& $('#freeModal form .errorlist').length > 0) {
					ajaxModals_handleForms();
				    }
				},
				error: genericAjaxError,
			    });
			    return false;
			});
		    };
		    ajaxModals_handleForms();
		}
	    });
	    return false;
	});
    });
}


// *****************************************
// Loaded in all pages

$(document).ready(function() {

    $("#togglebutton").click(function(e) {
	e.preventDefault();
	$("#wrapper").toggleClass("toggled");
    });

    loadPageScroll();
    formloaders();
    dateInputSupport();
    cuteFormNullBool();
    notificationsHandler();
    ajaxModals();

    // Dismiss popovers on click outside
    $('body').on('click', function (e) {
	if ($(e.target).data('toggle') !== 'popover'
	    && $(e.target).parents('.popover.in').length === 0
	    && $(e.target).data('manual-popover') != true) {
	    hidePopovers();
	}
    });

    $('#switchLanguage + .cuteform img').click(function() {
	$(this).closest('form').submit();
    });
});

// *****************************************
// *****************************************
// Tools to call

// *****************************************
// Load bootstrap

function loadToolTips() {
    $('[data-toggle="tooltip"]').tooltip();
}

function loadPopovers() {
    $('[data-toggle="popover"]').popover();
}

// *****************************************
// Get text

function gettext(term) {
    var translated_term = translated_terms[term]
    if (typeof translated_terms != 'undefined') {
	return translated_term;
    }
    return term;
}

// *****************************************
// Modal

// Use true for modal_size to not change the size
// Use 0 for buttons to remove all buttons
function freeModal(title, body, buttons, modal_size) {
    keep_size = modal_size === true;
    if (!keep_size) {
	$('#freeModal .modal-dialog').removeClass('modal-lg');
	$('#freeModal .modal-dialog').removeClass('modal-md');
	$('#freeModal .modal-dialog').removeClass('modal-sm');
	if (typeof modal_size != 'undefined') {
	    $('#freeModal .modal-dialog').addClass('modal-' + modal_size);
	} else {
	    $('#freeModal .modal-dialog').addClass('modal-lg');
	}
    }
    $('#freeModal .modal-header h4').html(title);
    $('#freeModal .modal-body').html(body);
    $('#freeModal .modal-footer').html('<button type="button" class="btn btn-main" data-dismiss="modal">OK</button>');
    if (buttons === 0) {
	$('#freeModal .modal-footer').hide();
    } else if (typeof buttons != 'undefined') {
	$('#freeModal .modal-footer').html(buttons);
	$('#freeModal .modal-footer').show();
    }
    $('#freeModal').modal('show');
}

// *****************************************
// Pagination

function load_more_function(nextPageUrl, newPageParameters, newPageCallback, onClick) {
    var button = $("#load_more");
    button.html('<div class="loader">Loading...</div>');
    var next_page = button.attr('data-next-page');
    $.get(nextPageUrl + location.search + (location.search == '' ? '?' : '&') + 'page=' + next_page + newPageParameters, function(data) {
	button.replaceWith(data);
	if (onClick) {
	    paginationOnClick(onClick, nextPageUrl, newPageParameters, newPageCallback);
	} else {
	    pagination(nextPageUrl, newPageParameters, newPageCallback);
	}
	if (typeof newPageCallback != 'undefined') {
	    newPageCallback();
	}
    });
}

function pagination(nextPageUrl, newPageParameters, newPageCallback) {
    var button = $("#load_more");
    $(window).scroll(
	function () {
	    if (button.length > 0
		&& button.find('.loader').length == 0
		&& ($(window).scrollTop() + $(window).height())
		>= ($(document).height() - button.height() - 600)) {
		load_more_function(nextPageUrl, newPageParameters, newPageCallback, false);
	    }
	});
}

function paginationOnClick(buttonId, nextPageUrl, newPageParameters, newPageCallback) {
    var button = $('#' + buttonId);
    button.unbind('click');
    button.click(function(e) {
	e.preventDefault();
	load_more_function(nextPageUrl, newPageParameters, newPageCallback, buttonId);
	return false;
    });
}

// *****************************************
// Reload disqus count

function reloadDisqus() {
    window.DISQUSWIDGETS = undefined;
    $.getScript('http://' + disqus_shortname + '.disqus.com/count.js');
}

// *****************************************
// Hide all the popovers

function hidePopovers() {
    $('[data-manual-popover=true]').popover('hide');
    $('[data-toggle=popover]').popover('hide');
    $('a[href="/notifications/"]').popover('destroy');
}

// *****************************************
// Load a bunch of cute forms

// Takes an object of key = form name and value = true if just value.png, callback otherwise (value, string)
function multiCuteForms(cuteformsToDo, withImages) {
    withImages = typeof withImages != 'undefined' ? withImages : true;
    for (var form in form_choices) {
	for (var field_name in form_choices[form]) {
	    if (field_name in cuteformsToDo) {
		var images = {};
		for (var value in form_choices[form][field_name]) {
		    if (value == '') {
			images[value] = empty_image;
		    } else {
			var cb = cuteformsToDo[field_name];
			if (cb === true) {
			    images[value] = static_url + 'img/' + field_name + '/' + value + '.png';
			    withImages = true;
			} else if (cb === 'name') {
			    images[value] = form_choices[form][field_name][value];
			    withImages = false;
			} else {
			    images[value] = cb(value, form_choices[form][field_name][value]);
			}
		    }
		}
		if (withImages) {
		    cuteform($('#id_' + field_name), {
			'images': images,
		    });
		} else {
		    if ('' in images) {
			images[''] = '<img src="' + images[''] + '">'
		    }
		    cuteform($('#id_' + field_name), {
			'html': images,
		    });
		}
	    }
	}
    }
}

function multiCuteFormsImages(cuteFormsToDo) {
    multiCuteForms(cuteFormsToDo, true);
}

function multiCuteFormsHTML(cuteFormsToDo) {
    multiCuteForms(cuteFormsToDo, false);
}

// *****************************************
// Generic ajax error

function genericAjaxError(xhr, ajaxOptions, thrownError) {
    alert(xhr.responseText);
}

// *****************************************
// Handle actions on activities view

function updateActivities() {
    loadPopovers();
    $('.activity .message').each(function() {
	if (!$(this).hasClass('markdowned')) {
	    applyMarkdown($(this));
	    $(this).addClass('markdowned');
	}
    });
    $('a[href=#likecount]').unbind('click');
    $('a[href=#likecount]').click(function(e) {
	e.preventDefault();
	var button = $(this);
	var socialbar = button.closest('.socialbar');
	var loader = socialbar.find('.hidden-loader');
	var activity_id = socialbar.closest('.activity').data('id');
	button.hide();
	loader.show();
	$.get('/ajax/users/?ajax_modal_only&liked_activity=' + activity_id, function(data) {
	    loader.hide();
	    button.show();
	    freeModal(gettext('Liked this activity'), data);
	});
	return false;
    });
    $('.likeactivity').unbind('submit');
    $('.likeactivity').submit(function(e) {
	e.preventDefault();
	var loader = $(this).find('.hidden-loader');
	var button = $(this).find('button[type=submit]');
	loader.width(button.width());
	button.hide();
	loader.show();
	$(this).ajaxSubmit({
	    context: this,
	    success: function(data) {
		if (data['result'] == 'liked' || data['result'] == 'unliked') {
		    if (data['result'] == 'liked') {
			$(this).find('input[type=hidden]').prop('name', 'unlike');
		    } else if (data['result'] == 'unliked') {
			$(this).find('input[type=hidden]').prop('name', 'like');
		    }
		    var value = button.html();
		    button.html(button.attr('data-reverse'));
		    button.attr('data-reverse', value);
		}
		loader.hide();
		button.show();
		if (typeof data['total_likes'] != 'undefined') {
		    $(this).find('a[href="#likecount"]').text(data['total_likes']);
		}
	    },
	    error: genericAjaxError,
	});
	return false;
    });
    if ($('#sidebar-wrapper #id_language').length > 0 && $('#sidebar-wrapper #id_language + .cuteform').length < 1) {
	multiCuteForms({
	    'language': true,
	});
    }
    reloadDisqus();
}

// *****************************************
// Markdown + AutoLink

var entityMap = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': '&quot;',
    "'": '&#39;',
    "/": '&#x2F;'
};

function escapeHtml(string) {
    return String(string).replace(/[&<>"'\/]/g, function (s) {
	return entityMap[s];
    });
}

function applyMarkdown(elt) {
    elt.html(Autolinker.link(marked(escapeHtml(elt.text())), { newWindow: true, stripPrefix: true } ));
}

// *****************************************
// Load Badges

function updateBadges() {
    ajaxModals();
}

function afterLoadBadges(user_id) {
    updateBadges();
    pagination('/ajax/badges/', '&of_user=' + user_id, updateCards);
}

function loadBadges(user_id, onDone) {
    $.get('/ajax/badges/?of_user=' + user_id, function(data) {
        if (data.trim() == "") {
	    onDone('<div class="padding20"><div class="alert alert-warning">' + gettext('No result.') + '</div></div>', loadBadges);
	} else {
	    onDone(data, afterLoadBadges);
	}
    });
}

// *****************************************
// iTunes

function pauseAllSongs() {
    $('audio').each(function() {
	$(this)[0].pause();
	$(this).closest('div').find('[href=#play] i').removeClass();
	$(this).closest('div').find('[href=#play] i').addClass('flaticon-play');
    });
}

function loadiTunesData(song, successCallback, errorCallback) {
    var itunes_id = song.find('[href=#play]').data('itunes-id');
    $.ajax({
	"url": 'https://itunes.apple.com/lookup',
	"dataType": "jsonp",
	"data": {
	    "id": itunes_id,
	},
	"error": function (jqXHR, textStatus, message) {
	    if (typeof errorCallback != 'undefined') {
		errorCallback();
	    }
	    alert('Oops! This music doesn\'t seem to be valid anymore. Please contact us and we will fix this.');
	},
	"success": function (data, textStatus, jqXHR) {
	    data = data['results'][0];
	    song.find('.itunes').find('.album').prop('src', data['artworkUrl60']);
	    song.find('.itunes').find('.itunes-link').prop('href', data['trackViewUrl'] + '&at=1001l8e6');
	    song.find('.itunes').show('slow');
	    song.find('audio source').prop('src', data['previewUrl'])
	    song.find('audio')[0].load();
	    playSongButtons();
	    successCallback(song, data);
	}
    });
}

function loadAlliTunesData(successCallback, errorCallback) {
    $('.song').each(function() {
	loadiTunesData($(this), successCallback, errorCallback);
    });
}

function playSongButtons() {
    $('audio').on('ended', function() {
	pauseAllSongs();
    });
    $('[href=#play]').unbind('click');
    $('[href=#play]').click(function(event) {
	event.preventDefault();
	var button = $(this);
	var button_i = button.find('i');
	var song = button.closest('.song');
	// Stop all previously playing audio
	if (button_i.prop('class') == 'flaticon-pause') {
	    pauseAllSongs();
	    return;
	}
	pauseAllSongs();
	if (song.find('audio source').attr('src') != '') {
	    song.find('audio')[0].play();
	    button_i.removeClass();
	    button_i.addClass('flaticon-pause');
	} else {
	    button_i.removeClass();
	    button_i.addClass('flaticon-loading');
	    loadiTunesData(song, function(data) {
		song.find('audio')[0].play();
		button_i.removeClass();
		button_i.addClass('flaticon-pause');
	    }, function() {
		button_i.removeClass();
		button_i.addClass('flaticon-play');
	    });
	}
	return false;
    });
}
