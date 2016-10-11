
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

function profileTabs() {
    $('#profiletabs li a').on('show.bs.tab', function (e) {
	var user_id = $('#username').data('user-id');
	if ($(e.target).attr('href') == '#profileactivities' && $('#activities').text() == "") {
	    $.get('/ajax/activities/?owner_id=' + user_id, function(html) {
		$('#activities').html(html);
		if ($.trim($('#activities').text()) == '') {
		    $('#activities').html('<div class="alert alert-warning">' + gettext('No result.') + '</div>');
		} else {
		    updateActivities();
		    pagination('/ajax/activities/', '&owner_id=' + user_id, updateActivities);
		}
	    });
	} else if ($(e.target).attr('href') != '#profileaccounts') {
	    var tab_name = $(e.target).attr('href').replace('#profile', '');
	    if ($('#profile' + tab_name).text() == "") {
		window[tab_callbacks[tab_name]](user_id, function(data, onDone) {
		    $('#profile' + tab_name).html(data);
		    if (typeof onDone != 'undefined') {
			onDone(user_id);
		    }
		});
	    }
	}
    });
}

$(document).ready(function() {
    handlefollow();
    loadPopovers();
    applyMarkdown($('.topprofile .description'));
    profileTabs();

    $('[href="#openBadges"]').click(function(e) {
	e.preventDefault();
	$('.nav-tabs [href="#profilebadges"]').tab('show');
	$('html, body').stop().animate({
	    scrollTop: $('#profilebadges').offset().top
	}, 1500, 'easeInOutExpo');
	return false;
    });
});
