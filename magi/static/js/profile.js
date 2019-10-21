
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
                    $('a[href*="?followers_of"] strong').text(data['total_followers']);
                    if (data['total_followers'] == 0) {
                        $('a[href*="?followers_of"]').hide();
                    } else {
                        $('a[href*="?followers_of"]').show();
                    }
                }
            },
            error: genericAjaxError,
        });
    });
}

function loadCollectionForOwner(load_url, callback) {
    return function(tab_name, user_id, onDone) {
        $.get(load_url + (load_url.includes('?') ? '&' : '?') + 'owner=' + user_id, function(data) {
            onDone(data, function() {
                if (callback) {
                    callback();
                }
                pagination(load_url, '&owner=' + user_id, callback);
            });
        });
    }
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
        $.get(load_url + '&ajax_modal_only&ajax_show_top_buttons&buttons_color=' + $('[data-account-id="' + account_id + '"]').data('color'), function(data) {
            onDone(data, function() {
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
        if (!account_tab_callbacks[account_id][tab_name]['called']) {
            var user_id = $('#username').data('user-id');
            account_elt.find('#account-' + account_id + '-tab-' + tab_name).html('<div class="loader"><i class="flaticon-loading"></i></div>');
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
});
