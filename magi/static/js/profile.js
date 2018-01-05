
function handlefollow() {
    $('#follow').submit(function(e) {
	e.preventDefault();
	var loader = $('#follow-hidden-loader');
	var button = $('#follow input[type="submit"]');
	loader.width(button.width());
	button.hide();
	loader.show();
	$(this).ajaxSubmit({
	    success: function(data) {
		if (data['result'] == 'followed' || data['result'] == 'unfollowed') {
		    if (data['result'] == 'followed') {
			$('#follow input[type="hidden"]').prop('name', 'unfollow');
		    } else if (data['result'] == 'unfollowed') {
			$('#follow input[type="hidden"]').prop('name', 'follow');
		    }
		    var value = button.prop('value');
		    button.prop('value', button.attr('data-reverse'));
		    button.attr('data-reverse', value);
		}
		loader.hide();
		button.show();
		if (typeof data['total_followers'] != 'undefined') {
		    $('a[href="#followers"] strong').text(data['total_followers']);
		    if (data['total_followers'] == 0) {
			$('a[href="#followers"]').hide();
		    } else {
			$('a[href="#followers"]').show();
		    }
		}
	    },
	    error: genericAjaxError,
	});
    });

    $('a[href="#followers"]').click(function(e) {
	e.preventDefault();
	var username = $('#username').text();
	var text = $(this).text();
	$.get('/ajax/users/?ajax_modal_only&followers_of=' + username, function(data) {
	    freeModal(username + ': ' + text, data, 0);
	});
    });
    $('a[href="#following"]').click(function(e) {
	e.preventDefault();
	var username = $('#username').text();
	var text = $(this).text();
	$.get('/ajax/users/?ajax_modal_only&followed_by=' +  username, function(data) {
	    freeModal(username + ': ' + text, data, 0);
	});
    });
}

function profileLoadActivities(tab_name, user_id, onDone) {
    $.get('/ajax/activities/?owner_id=' + user_id, function(html) {
	$('#activities').html(html);
	if ($.trim($('#activities').text()) == '') {
	    $('#activities').html('<div class="alert alert-warning">' + gettext('No result.') + '</div>');
	} else {
	    updateActivities();
	    pagination('/ajax/activities/', '&owner_id=' + user_id, updateActivities);
	}
	onDone(undefined, undefined);
    });
}

function loadCollectionForOwner(load_url, callback) {
    return function(tab_name, user_id, onDone) {
        $.get(load_url + '?owner=' + user_id, function(data) {
            onDone($.trim(data) === '' ? '<div class="alert alert-warning">' + gettext('No result.') + '</div>' : data, function() {
                if (callback) {
                    callback();
                }
                pagination(load_url, '&owner=' + user_id, callback);
            });
        });
    }
    $.get('/ajax/activities/?owner_id=' + user_id, function(html) {
	$('#activities').html(html);
	if ($.trim($('#activities').text()) == '') {
	    $('#activities').html();
	} else {
	    updateActivities();
	    pagination('/ajax/activities/', '&owner_id=' + user_id, updateActivities);
	}
	onDone(undefined, undefined);
    });
}

function onProfileTabOpened() {
    var tab_name = $('#profiletabs+.tab-content>.tab-pane.active').data('tab-name');
    if (typeof tab_callbacks[tab_name] != 'undefined') {
	if (!tab_callbacks[tab_name]['called']) {
	    var user_id = $('#username').data('user-id');
	    $('#profile' + tab_name).html('<div class="loader"><i class="flaticon-loading"></i></div>');
	    tab_callbacks[tab_name]['callback'](tab_name, user_id, function(data, onDone) {
		if (typeof data != 'undefined') {
		    $('#profile' + tab_name).html(data);
		}
		if (typeof onDone != 'undefined') {
		    onDone(user_id);
		}
		loadCommons();
	    });
	    tab_callbacks[tab_name]['called'] = true;
	}
    }
}

function loadCollectionForAccount(load_url, callback) {
    return function(tab_name, user_id, account_id, onDone) {
        $.get(load_url + '&ajax_modal_only', function(data) {
            onDone($.trim(data) === '' ? '<div class="alert alert-warning">' + gettext('No result.') + '</div>' : data, function() {
                if (callback) {
                    callback();
                }
            });
        });
    }
}

function onProfileAccountTabOpened(account_elt) {
    var account_id = account_elt.data('account-id');
    var tab_name = account_elt.find('.tab-content>.tab-pane.active').data('tab-name');
    if (account_tab_callbacks
        && account_tab_callbacks[account_id]
        && typeof account_tab_callbacks[account_id][tab_name] != 'undefined') {
        account_elt.find('#account-' + account_id + '-tab-' + tab_name).html('<div class="loader"><i class="flaticon-loading"></i></div>');
	if (!account_tab_callbacks[account_id][tab_name]['called']) {
	    var user_id = $('#username').data('user-id');
	    account_tab_callbacks[account_id][tab_name]['callback'](tab_name, user_id, account_id, function(data, onDone) {
		if (typeof data != 'undefined') {
                    account_elt.find('#account-' + account_id + '-tab-' + tab_name).html(data);
		}
		if (typeof onDone != 'undefined') {
		    onDone(user_id, account_id);
		}
		loadCommons();
	    });
	    account_tab_callbacks[account_id][tab_name]['called'] = true;
	}
    }
}

$(document).ready(function() {
    handlefollow();
    onProfileTabOpened();
    $('#profiletabs li a').on('shown.bs.tab', function (e) {
	onProfileTabOpened();
    });
    $('.panel-default-account').each(function() {
        var account_elt = $(this);
        onProfileAccountTabOpened(account_elt);
        account_elt.find('.account-tabs li a').on('shown.bs.tab', function (e) {
	    onProfileAccountTabOpened(account_elt);
        });
    });
    $('[href="#openBadges"]').click(function(e) {
	e.preventDefault();
	$('.nav-tabs [href="#profilebadge"]').tab('show');
	$('html, body').stop().animate({
	    scrollTop: $('#profilebadge').offset().top
	}, 1500, 'easeInOutExpo');
	return false;
    });
});
