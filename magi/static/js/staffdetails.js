function _hideDetails() {
    let formGroup = $(this).closest('.form-group');
    let label = formGroup.find('label');
    formGroup.find('.help-block').hide();
    label.html(label.html().replace('(Only staff can see it)', ''));
}

function _switchBold() {
    let formGroup = $(this).closest('.form-group');
    formGroup.find('label').css('font-weight', 'normal');
    formGroup.find('.help-block').css('font-weight', 'bold');
    formGroup.find('.help-block').css('margin-left', '-50%');;
    formGroup.find('.help-block').css('width', '150%');;
}

function updateStaffDetailsForm() {
    $.each(['availability', 'weekend_availability'], function(_, i) {
        let selector = $('[id^="id_d_' + i + '-"]');
        selector.each(_switchBold);
        selector.not(":eq(0)").each(_hideDetails);
    });
}
