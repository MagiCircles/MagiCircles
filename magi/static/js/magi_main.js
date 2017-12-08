
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

// *****************************************
// Smooth page scroll

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
// Check if date input is supported and add an help text otherwise

function dateInputSupport() {
    if ($('input[type="date"]').length > 0) {
        var input = document.createElement('input');
        input.setAttribute('type', 'date');
        if (input.type == 'date') {
	    $('input[type="date"]').parent().find('.help-block').hide();
        }
    }
}

// *****************************************
// Hide Staff Buttons

function hideStaffButtons(show, showTooltip /* optional, = true */) {
    if ($('.staff-only').length > 0) {
	show = typeof show == 'undefined' ? false : show;
	if (show) {
	    $('.staff-only').show('slow');
	} else {
	    $('.staff-only').hide('slow');
	}
	$('a[href="#hideStaffButtons"]').show('slow', function() {
	    loadToolTips();
	    if (typeof showTooltip == 'undefined' || showTooltip == true) {
		$('a[href="#hideStaffButtons"]').tooltip('show');
		setTimeout(function() {
		    $('a[href="#hideStaffButtons"]').tooltip('hide');
		}, 2000);
	    }
	});
	$('a[href="#hideStaffButtons"]').unbind('click');
	$('a[href="#hideStaffButtons"]').click(function(e) {
	    e.preventDefault();
	    $(this).blur();
	    hideStaffButtons(!show);
	    return false;
	});
	staff_buttons_hidden = !show;
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

// *****************************************
// Ajax modals

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
		if (typeof button.attr('href') != 'undefined') {
		    $('#freeModal').data('original-url', button.attr('href'));
		}
                loadCommons();
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
// Load countdowns

function _loadCountdowns() {
    $('.countdown').each(function() {
	var elt = $(this);
	var format = typeof elt.data('format') != undefined ? elt.data('format') : '{time}';
	elt.countdown({
	    date: elt.data('date'),
	    render: function(data) {
		$(this.el).text(format.replace('{time}', data.days + ' ' + gettext('days') + ' ' + data.hours + ' ' + gettext('hours') + ' ' + data.min + ' ' + gettext('minutes') + ' ' + data.sec + ' ' + gettext('seconds')));
	    },
	});
    });
}

function loadCountdowns() {
    if ($('.countdown').length > 0) {
	if (typeof Countdown == 'undefined') {
	    $.getScript(static_url + 'bower/countdown/dest/jquery.countdown.min.js', _loadCountdowns);
	} else {
	    _loadCountdowns();
	}
    }
}

// *****************************************
// Load timezone dates

function _loadTimezones() {
    $('.timezone').each(function() {
	var elt = $(this);
	if (elt.data('converted') == true) {
	    return;
	}
	elt.data('converted', true);
	var date = new Date(elt.find('.datetime').text());
	var timezone = elt.data('to-timezone');
	var options = {
	    year: 'numeric',
	    month: 'long',
	    day: 'numeric',
	    hour: 'numeric',
	    minute: 'numeric',
	};
	if (typeof timezone != 'undefined' && timezone != '' && timezone != 'Local time') {
	    options['timeZone'] = timezone;
	} else {
	    timezone = 'Local time';
	}
	var converted_date = date.toLocaleString($('html').attr('lang'), options);
	elt.find('.datetime').text(converted_date);
	elt.find('.current_timezone').text(gettext(timezone));
	if (typeof elt.data('timeago') != 'undefined') {
	    var html = elt.html();
	    elt.html(jQuery.timeago(date));
	    elt.tooltip({
		html: true,
		title: html,
		trigger: 'hover',
	    });
	}
	elt.show();
    });
}

function loadTimezones() {
    if ($('[data-timeago]').length > 0 && typeof jQuery.timeago == 'undefined') {
	$.getScript(static_url + 'bower/jquery-timeago/jquery.timeago.js', function() {
	    $.getScript(static_url + 'bower/jquery-timeago/locales/jquery.timeago.' + $('html').attr('lang')+ '.js', _loadTimezones);
	});
    } else {
	_loadTimezones();
    }
}

// *****************************************
// On back button close modal

var realBack = false;
var calledBack = false;

function onBackButtonCloseModal() {
    $('.modal').on('shown.bs.modal', function()  {
	var urlReplace;
	var original_url = $(this).data('original-url');
	if (typeof original_url != 'undefined') {
	    urlReplace = original_url;
	} else {
	    urlReplace = '#' + $(this).attr('id');
	}
	history.pushState(null, null, urlReplace);
    });

    $('.modal').on('hidden.bs.modal', function()  {
	if (realBack == false) {
	    calledBack = true;
	    history.back();
	} else {
	    realBack = false;
	}
    });
    $(window).on('popstate', function() {
	if (calledBack == false) {
	    realBack = true;
	}
	calledBack = false;
	$('.modal').modal('hide');
    });
}

// *****************************************
// Side bar toggle button

function sideBarToggleButton() {
    $('#togglebutton, .togglebutton').click(function(e) {
	e.preventDefault();
	$('#wrapper').toggleClass('toggled');
	$(this).blur();
    });
}

// *****************************************
// Switch language

function switchLanguage() {
    $('#switchLanguage + .cuteform img').click(function() {
	$(this).closest('form').submit();
    });
}

// *****************************************
// Items reloaders

function itemsReloaders() {
    if (typeof ids_to_reload != 'undefined') {
        $.each(reload_urls_start_with, function(index, url_start_with) {
            $('[href^="' + url_start_with + '"]:not(.reload-handler)').click(function(e) {
                var item_id = $(this).closest('[data-item-id]').data('item-id');
                ids_to_reload.push(item_id);
                $(this).addClass('reload-handler');
            });
        });
    }
    if (typeof reload_item != 'undefined') {
        $.each(reload_urls_start_with, function(index, url_start_with) {
            $('[href^="' + url_start_with + '"]:not(.reload-item-handler)').click(function(e) {
                reload_item = true;
                $(this).addClass('reload-item-handler');
            });
        });
    }
}

function modalItemsReloaders() {
    if (typeof ids_to_reload != 'undefined') {
        $('.modal').on('hidden.bs.modal', function(e) {
            ids_to_reload = $.unique(ids_to_reload);
            if (ids_to_reload.length > 0) {
                $.get(ajax_reload_url + '?ids=' + ids_to_reload.join(',')
                      + '&page_size=' + ids_to_reload.length, function(data) {
                          var html = $(data);
                          $.each(ids_to_reload, function(index, id) {
                              var previous_item = $('[data-item="' + reload_data_item + '"][data-item-id="' + id + '"]');
                              var new_item = html.find('[data-item="' + reload_data_item + '"][data-item-id="' + id + '"]');
                              if (new_item.length == 0) {
                                  // If not returned, remove it
                                  previous_item.remove();
                              } else {
                                  // Replace element
                                  previous_item.replaceWith(new_item);
                              }
                          });
                          ids_to_reload = [];
                          if (ajax_pagination_callback) {
                              ajax_pagination_callback();
                          }
                          loadCommons();
                      });
            }
        });
    }
    if (typeof reload_item != 'undefined') {
        $('.modal').on('hidden.bs.modal', function(e) {
            if (reload_item === true) {
                $.get(ajax_reload_url, function(data) {
                    $('.item-container').html(data);
                    reload_item = false;
                    loadCommons();
                });
            }
        });
    }
}

// *****************************************
// Dismiss popovers on click outside

function dismissPopoversOnClickOutside() {
    $('body').on('click', function (e) {
	if ($(e.target).data('toggle') !== 'popover'
	    && $(e.target).parents('.popover.in').length === 0
	    && $(e.target).data('manual-popover') != true) {
	    hidePopovers();
	}
    });
}

// *****************************************
// Load commons on modal shown

function loadCommonsOnModalShown() {
    $('.modal').on('shown.bs.modal', function (e) {
    	loadCommons();
    });
}

function hideCommonsOnModalShown() {
    $('#freeModal').on('show.bs.modal', function() {
	$('main [data-toggle="tooltip"]').tooltip('hide');
	$('main [data-toggle="popover"]').popover('hide');
    });
}

// *****************************************
// Loaded in all pages

$(document).ready(function() {
    loadCommons(true);
    modalItemsReloaders();
    notificationsHandler();
    sideBarToggleButton();
    onBackButtonCloseModal();
    loadCommonsOnModalShown();
    hideCommonsOnModalShown();
    loadPageScroll();
    dismissPopoversOnClickOutside();
    switchLanguage();
});

// *****************************************
// *****************************************
// Tools to call

// *****************************************
// Reload common things, called:
// - on load of any page
// - when a view is loaded in a modal
// - when a new pagination page is loaded

function loadCommons(onPageLoad /* optional = false */) {
    onPageLoad = typeof onPageLoad == 'undefined' ? false : onPageLoad;
    loadToolTips();
    loadPopovers();
    formloaders();
    dateInputSupport();
    hideStaffButtons(false, onPageLoad);
    ajaxModals();
    loadCountdowns();
    loadTimezones();
    loadMarkdown();
    reloadDisqus();
    itemsReloaders();
}

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
    if (typeof translated_term != 'undefined') {
	return translated_term;
    }
    return term;
}

// *****************************************
// Modal

// Use true for modal_size to not change the size
// Use 0 for buttons to remove all buttons
function freeModal(title, body, buttons /* optional */, modal_size /* optional */) {
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

function confirmModal(onConfirmed, onCanceled /* optional */, title /* optional */, body /* optional */) {
    title = typeof title == 'undefined' ? gettext('Confirm') : title;
    body = typeof body == 'undefined' ? gettext('You can\'t cancel this action afterwards.') : body;
    freeModal(title, body, '\
<button type="button" class="btn btn-default">' + gettext('Cancel') + '</button>\
<button type="button" class="btn btn-danger">' + gettext('Confirm') + '</button>');
   $('#freeModal .modal-footer .btn-danger').click(function() {
	onConfirmed();
	$('#freeModal').modal('hide');
    });
    $('#freeModal .modal-footer .btn-default').click(function() {
	if (typeof onCanceled != 'undefined') {
	    onCanceled();
	}
	$('#freeModal').modal('hide');
    });
}

// *****************************************
// Pagination

function load_more_function(nextPageUrl, newPageParameters, newPageCallback /* optional */, onClick) {
    var button = $('#load_more');
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
	loadCommons();
    });
}

function pagination(nextPageUrl, newPageParameters, newPageCallback /* optional */) {
    var button = $('#load_more');
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

function paginationOnClick(buttonId, nextPageUrl, newPageParameters, newPageCallback /* optional */) {
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
    if ($('[href$="#disqus_thread"], .disqus-comment-count').length > 0) {
	window.DISQUSWIDGETS = undefined;
	$.getScript('http://' + disqus_shortname + '.disqus.com/count.js');
    }
}

// *****************************************
// Hide all the popovers

function hidePopovers() {
    $('[data-manual-popover=true]').popover('hide');
    $('[data-toggle=popover]').popover('hide');
    $('a[href="/notifications/"]').popover('destroy');
}

// *****************************************
// Generic ajax error

function genericAjaxError(xhr, ajaxOptions, thrownError) {
    alert(xhr.responseText);
}

// *****************************************
// Handle actions on activities view

function updateActivities() {
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

function _loadMarkdown() {
    $('.to-markdown:not(.markdowned)').each(function() {
	applyMarkdown($(this));
	$(this).addClass('markdowned');
    });
}

function loadMarkdown() {
    if ($('.to-markdown').length > 0) {
	if (typeof marked == 'undefined') {
	    $.getScript(static_url + 'bower/marked/lib/marked.js', _loadMarkdown);
	} else {
	    _loadMarkdown();
	}
    }
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
