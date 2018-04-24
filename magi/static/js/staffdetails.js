
function updateStaffDetailsForm() {
    $.each(['availability', 'weekend_availability'], function(_, i) {
        let selector = $('[id^="id_d_' + i + '-"]');
        d_FieldCheckBoxes(selector, true);
        selector.not(":eq(0)").each(function() {
            let label = $(this).closest('.form-group').find('label');
            label.html(label.html().replace('(Only staff can see it)', ''));
        });
    });
}
