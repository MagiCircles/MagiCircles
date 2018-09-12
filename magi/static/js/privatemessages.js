function loadPrivateMessages() {
    // Show "End of new messages" separator
    $('.title-separator').remove();
    let last_message = $('.is-new-message').last().closest('.private-message').closest('.row');
    if (last_message.next('.row').length) {
        last_message.after(
            '<div class="title-separator"><span>' + (
                gettext('End of new messages')
            ) + '</span></div>');
    }

    // Render links into clickable links
    $('.private-message:not(.linked)').each(function() {
        let content = $(this).find('.message-content');
        content.html(Autolinker.link(content.text(), { newWindow: true, stripPrefix: true } ));
        $(this).addClass('linked');
    });
}
