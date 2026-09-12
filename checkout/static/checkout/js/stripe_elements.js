var stripePublicKey = $('#id_stripe_public_key').text().slice(1, -1);
var clientSecret = $('#id_client_secret').text().slice(1, -1);
var stripe = Stripe(stripePublicKey);
var elements = stripe.elements();

var style = {
    base: {
        color: '#000',
        fontFamily: '"Helvetica Neue", Helvetica, sans-serif',
        fontSmoothing: 'antialiased',
        fontSize: '16px',
        '::placeholder': {
            color: '#aab7c4'
        }
    },
    invalid: {
        color: '#dc3545',
        iconColor: '#dc3545'
    }
};

var card = elements.create('card', { style: style, hidePostalCode: true });
card.mount('#card-element');

// Handle realtime validation errors on the card element
card.addEventListener('change', function (event) {
    var errorDiv = document.getElementById('card-errors');
    if (event.error) {
        var html = `
            <span class="icon" role="alert">
                <i class="fas fa-times"></i>
            </span>
            <span>${event.error.message}</span>
        `;
        $(errorDiv).html(html);
    } else {
        errorDiv.textContent = '';
    }
});

// Handle form submit
var form = document.getElementById('payment-form');

form.addEventListener('submit', function (ev) {
    ev.preventDefault();
    card.update({ disabled: true });
    $('#submit-button').attr('disabled', true);
    // jQuery's slim build (what this site loads) has no fadeIn/fadeOut -
    // toggle a CSS-transition class and use plain show/hide instead.
    $('#payment-form').addClass('payment-form-fade');
    $('#loading-overlay').show();

    var saveInfo = Boolean($('#id-save-info').attr('checked'));
    var csrfToken = $('input[name="csrfmiddlewaretoken"]').val();
    var postData = {
        csrfmiddlewaretoken: csrfToken,
        client_secret: clientSecret,
        save_info: saveInfo,
        // Stripe's address object requires a 2-letter ISO country code,
        // which this project's free-text country field can't guarantee,
        // so country is never sent to Stripe at all (see below). Stash
        // the real value here instead, where the webhook handler can
        // recover it without Stripe's validation ever seeing it.
        country: form.country.value.trim(),
    };
    var url = '/checkout/cache_checkout_data/';

    // Stash the bag/save-info on the payment intent's metadata first, so
    // the webhook handler can recover them even if the form below never
    // actually submits (e.g. the user closes the tab right after paying).
    // jQuery's slim build (what this site loads) has no $.post/$.ajax -
    // use fetch() instead, same as the bag page's live updates.
    fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: new URLSearchParams(postData),
    }).then(function (response) {
        if (!response.ok) { throw new Error('Failed to cache checkout data'); }
        return stripe.confirmCardPayment(clientSecret, {
            payment_method: {
                card: card,
                billing_details: {
                    name: form.full_name.value.trim(),
                    phone: form.phone_number.value.trim(),
                    email: form.email.value.trim(),
                    address: {
                        line1: form.street_address1.value.trim(),
                        line2: form.street_address2.value.trim(),
                        city: form.town_or_city.value.trim(),
                        // No country here: Stripe requires a 2-letter ISO
                        // code if this is set at all, but this project's
                        // country field is free text ("Ireland", not "IE"),
                        // so sending it makes Stripe reject the whole
                        // payment with a 400. Omitting it is valid.
                        state: form.county.value.trim(),
                    }
                }
            },
            shipping: {
                name: form.full_name.value.trim(),
                phone: form.phone_number.value.trim(),
                address: {
                    line1: form.street_address1.value.trim(),
                    line2: form.street_address2.value.trim(),
                    city: form.town_or_city.value.trim(),
                    state: form.county.value.trim(),
                    postal_code: form.postcode.value.trim(),
                }
            }
        });
    }).then(function (result) {
        if (result.error) {
            var errorDiv = document.getElementById('card-errors');
            var html = `
                <span class="icon" role="alert">
                    <i class="fas fa-times"></i>
                </span>
                <span>${result.error.message}</span>
            `;
            $(errorDiv).html(html);
            card.update({ disabled: false });
            $('#submit-button').attr('disabled', false);
            $('#payment-form').removeClass('payment-form-fade');
            $('#loading-overlay').hide();
        } else {
            if (result.paymentIntent.status === 'succeeded') {
                form.submit();
            }
        }
    }).catch(function () {
        // Something went wrong caching the checkout data (or an
        // unexpected error calling Stripe) - reload to show the error
        // message from the view rather than risk charging the card
        // without the data we need to create the order.
        location.reload();
    });
});
