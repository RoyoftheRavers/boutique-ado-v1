from django.shortcuts import render, redirect, reverse, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.template.loader import render_to_string

from products.models import Product
from .contexts import bag_contents

# Create your views here.

def view_bag(request):
    """ A view that renders the shopping bag contents page """

    return render(request, 'bag/bag.html')

def add_to_bag(request, item_id):
    " A view to add a quantity of a specified product to the shopping bag"

    product = get_object_or_404(Product, pk=item_id)
    quantity = int(request.POST.get('quantity'))
    redirect_url = request.POST.get('redirect_url')
    size = None
    if 'product_size' in request.POST:
        size = request.POST['product_size']
    bag = request.session.get('bag', {})

    if size:
        if item_id in list(bag.keys()):
            if size in bag[item_id]['items_by_size'].keys():
                bag[item_id]['items_by_size'][size] += quantity
                messages.success(
                    request,
                    f'Updated size {size.upper()} {product.name} quantity to {bag[item_id]["items_by_size"][size]}')
            else:
                bag[item_id]['items_by_size'][size] = quantity
                messages.success(request, f'Added size {size.upper()} {product.name} to your bag')
        else:
            bag[item_id] = {'items_by_size': {size: quantity}}
            messages.success(request, f'Added size {size.upper()} {product.name} to your bag')
    else:
        if item_id in list(bag.keys()):
            bag[item_id] += quantity
            messages.success(request, f'Updated {product.name} quantity to {bag[item_id]}')
        else:
            bag[item_id] = quantity
            messages.success(request, f'Added {product.name} to your bag')

    request.session['bag'] = bag
    return redirect(redirect_url)


def adjust_bag(request, item_id):
    """Adjust the quantity of the specified product, removing it if the new quantity is 0"""

    quantity = int(request.POST.get('quantity'))
    size = None
    if 'product_size' in request.POST:
        size = request.POST['product_size']
    bag = request.session.get('bag', {})
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'

    try:
        product = get_object_or_404(Product, pk=item_id)

        if size:
            if quantity > 0:
                bag[item_id]['items_by_size'][size] = quantity
                message = f'Updated size {size.upper()} {product.name} quantity to {quantity}'
            else:
                del bag[item_id]['items_by_size'][size]
                if not bag[item_id]['items_by_size']:
                    bag.pop(item_id)
                message = f'Removed size {size.upper()} {product.name} from your bag'
        else:
            if quantity > 0:
                bag[item_id] = quantity
                message = f'Updated {product.name} quantity to {quantity}'
            else:
                bag.pop(item_id)
                message = f'Removed {product.name} from your bag'

        request.session['bag'] = bag

        # AJAX requests (the bag page's live quantity/remove updates) don't
        # reload the page, so a queued Django message would just pile up
        # until the next full navigation. Render the same toast template
        # server-side instead and let the frontend show it immediately.
        if is_ajax:
            toast_html = render_to_string(
                'includes/toasts/toast_success.html', {'message': message}, request=request)
        else:
            messages.success(request, message)
    except Exception as e:
        error_message = f'Error updating item: {e}'
        if is_ajax:
            toast_html = render_to_string(
                'includes/toasts/toast_error.html', {'message': error_message}, request=request)
            return JsonResponse({'error': str(e), 'toast_html': toast_html}, status=500)
        messages.error(request, error_message)
        return redirect(reverse('view_bag'))

    if is_ajax:
        context = bag_contents(request)
        item_subtotal = 0
        for bag_item in context['bag_items']:
            if str(bag_item['item_id']) == str(item_id) and bag_item.get('size') == size:
                item_subtotal = bag_item['subtotal']
                break
        return JsonResponse({
            'quantity': quantity,
            'removed': quantity <= 0,
            'item_subtotal': float(item_subtotal),
            'total': float(context['total']),
            'delivery': float(context['delivery']),
            'grand_total': float(context['grand_total']),
            'free_delivery_delta': float(context['free_delivery_delta']),
            'product_count': context['product_count'],
            'toast_html': toast_html,
        })

    return redirect(reverse('view_bag'))
