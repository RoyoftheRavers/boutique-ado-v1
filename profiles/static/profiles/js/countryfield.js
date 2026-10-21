// The country select's own collapsed/displayed value needs to be grey
// when the blank placeholder option is selected and black otherwise.
// CSS alone can't react to which option is currently selected, so this
// sets the color on load and again on every change.
var countryField = $('#id_default_country');
var defaultCountrySelected = countryField.val();

if (!defaultCountrySelected) {
    countryField.css('color', '#aab7c4');
}

countryField.change(function () {
    var countrySelected = $(this).val();
    if (!countrySelected) {
        $(this).css('color', '#aab7c4');
    } else {
        $(this).css('color', '#000');
    }
});
