import json
import time

from django.conf import settings
from django.http import HttpResponse

import stripe

from .models import Order, OrderLineItem
from products.models import Product
from profiles.models import UserProfile


class StripeWH_handler:
    """ Handle Stripe webhooks """

    def __init__(self, request):
        self.request = request

    def handle_event(self, event):
        """
        Handle a generic/unknown/unexpected webhook event
        """
        return HttpResponse(
            content=f'Unhandled webhook received: {event["type"]}',
            status=200)

    def handle_payment_intent_succeeded(self, event):
        """
        Handle the payment_intent.succeeded webhook from Stripe.

        Ensures the order exists in the database - the view normally
        creates it when the form submits, but if the user closes the tab
        after paying and before that submission completes, this recreates
        it from the data stashed on the payment intent's metadata.
        """
        intent = event.data.object
        pid = intent.id
        bag = intent.metadata.bag
        save_info = intent.metadata.save_info
        username = intent.metadata.username

        # Allow anonymous checkouts through the webhook too - profile stays
        # None for them, same as the checkout_success view.
        profile = None
        if username != 'AnonymousUser':
            profile = UserProfile.objects.get(user__username=username)

        # This API version doesn't expand `charges` on the PaymentIntent
        # (that field no longer exists) - billing_details now lives on the
        # PaymentMethod, so re-fetch with it expanded to get it.
        stripe.api_key = settings.STRIPE_SECRET_KEY
        intent = stripe.PaymentIntent.retrieve(pid, expand=['payment_method'])
        billing_details = intent.payment_method.billing_details
        shipping_details = intent.shipping
        grand_total = round(intent.amount / 100, 2)

        # country is never sent to Stripe's address object (it requires a
        # 2-letter ISO code, which this project's free-text field can't
        # guarantee) - recover the real value from our own metadata instead.
        country = intent.metadata.country

        # Clean data in shipping details - Stripe returns blank strings,
        # Django needs None for the nullable fields. This SDK version's
        # Address object isn't a dict (no .items()/__setitem__), so iterate
        # via to_dict() and mutate through setattr instead.
        for field, value in shipping_details.address.to_dict().items():
            if value == "":
                setattr(shipping_details.address, field, None)

        order_exists = False
        attempt = 1
        while attempt <= 5:
            try:
                order = Order.objects.get(
                    full_name__iexact=shipping_details.name,
                    email__iexact=billing_details.email,
                    phone_number__iexact=shipping_details.phone,
                    country__iexact=country,
                    postcode__iexact=shipping_details.address.postal_code,
                    town_or_city__iexact=shipping_details.address.city,
                    street_address1__iexact=shipping_details.address.line1,
                    street_address2__iexact=shipping_details.address.line2,
                    county__iexact=shipping_details.address.state,
                    grand_total=grand_total,
                    original_bag=bag,
                    stripe_pid=pid,
                )
                order_exists = True
                break
            except Order.DoesNotExist:
                attempt += 1
                time.sleep(1)

        if order_exists:
            return HttpResponse(
                content=f'Webhook received: {event["type"]} | SUCCESS: Verified order already in database',
                status=200)
        else:
            # metadata values are always strings, so this must be compared
            # against the literal 'true' - a non-empty 'false' string would
            # otherwise be truthy too.
            if profile is not None and save_info == 'true':
                profile.default_phone_number = shipping_details.phone
                profile.default_country = country
                profile.default_postcode = shipping_details.address.postal_code
                profile.default_town_or_city = shipping_details.address.city
                profile.default_street_address1 = shipping_details.address.line1
                profile.default_street_address2 = shipping_details.address.line2
                profile.default_county = shipping_details.address.state
                profile.save()

            order = None
            try:
                order = Order.objects.create(
                    full_name=shipping_details.name,
                    user_profile=profile,
                    email=billing_details.email,
                    phone_number=shipping_details.phone,
                    country=country,
                    postcode=shipping_details.address.postal_code,
                    town_or_city=shipping_details.address.city,
                    street_address1=shipping_details.address.line1,
                    street_address2=shipping_details.address.line2,
                    county=shipping_details.address.state,
                    original_bag=bag,
                    stripe_pid=pid,
                )
                for item_id, item_data in json.loads(bag).items():
                    product = Product.objects.get(id=item_id)
                    if isinstance(item_data, int):
                        OrderLineItem.objects.create(
                            order=order,
                            product=product,
                            quantity=item_data,
                        )
                    else:
                        for size, quantity in item_data['items_by_size'].items():
                            OrderLineItem.objects.create(
                                order=order,
                                product=product,
                                quantity=quantity,
                                product_size=size,
                            )
            except Exception as e:
                if order:
                    order.delete()
                return HttpResponse(content=f'Webhook received: {event["type"]} | ERROR: {e}', status=500)
        return HttpResponse(
            content=f'Webhook received: {event["type"]} | SUCCESS: Created order in webhook',
            status=200)

    def handle_payment_intent_payment_failed(self, event):
        """
        Handle the payment_intent.payment_failed webhook from Stripe
        """
        return HttpResponse(
            content=f'Webhook received: {event["type"]}',
            status=200)
