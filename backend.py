"""Function-based order processing; money uses decimal arithmetic."""
from decimal import Decimal, ROUND_HALF_UP


def money(value):
    return Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def sum_amounts(*amounts):
    """Combine monetary amounts, including an empty collection."""
    return sum(amounts, Decimal('0.00'))


def calculate_order_subtotal(order, products):
    return sum_amounts(*(money(products[item['product_id']]['price']) * item['quantity']
                         for item in order['items']))


def calculate_discount(subtotal):
    rate = '0.15' if subtotal >= 1000 else '0.10' if subtotal >= 500 else '0.05' if subtotal >= 200 else '0'
    return money(subtotal * Decimal(rate))


def calculate_shipping(subtotal):
    return money(0 if subtotal >= 500 else 20)


def validate_order(order, products):
    """Return errors, aggregating repeated product lines before checking stock."""
    if not isinstance(order, dict):
        return ['Order must be a dictionary.']
    errors = []
    for field in ('order_id', 'customer'):
        if not isinstance(order.get(field), str) or not order[field].strip():
            errors.append(f'{field} must be a nonempty string.')
    if order.get('payment_status') not in ('paid', 'pending'):
        errors.append('Payment status must be paid or pending.')
    items = order.get('items')
    if not isinstance(items, list) or not items:
        return errors + ['Order must contain a nonempty items list.']
    quantities = {}
    for item in items:
        if not isinstance(item, dict):
            errors.append('Each item must be a dictionary.')
            continue
        product_id = item.get('product_id')
        if not isinstance(product_id, str) or product_id not in products:
            errors.append('Unknown product ID.')
            continue
        quantity = item.get('quantity')
        if type(quantity) is not int or quantity <= 0:
            errors.append('Quantity must be a positive integer.')
            continue
        quantities[product_id] = quantities.get(product_id, 0) + quantity
    for product_id, quantity in quantities.items():
        if quantity > products[product_id]['stock']:
            errors.append(f'Insufficient stock for {product_id}.')
    return errors


def process_order(order, products, **options):
    """Process one order. Only successful paid orders mutate inventory."""
    unknown = set(options) - {'include_shipping', 'apply_discount'}
    if unknown or any(type(value) is not bool for value in options.values()):
        raise ValueError('Options must be include_shipping/apply_discount booleans.')
    errors = validate_order(order, products)
    result = {
        'order_id': order.get('order_id') if isinstance(order, dict) else None,
        'customer': order.get('customer') if isinstance(order, dict) else None,
        'status': 'rejected', 'errors': errors, 'items': [],
        'subtotal': money(0), 'discount': money(0), 'shipping': money(0), 'total': money(0),
    }
    if errors:
        return result
    subtotal = calculate_order_subtotal(order, products)
    discount = calculate_discount(subtotal) if options.get('apply_discount', True) else money(0)
    shipping = calculate_shipping(subtotal) if options.get('include_shipping', True) else money(0)
    result.update(status=order['payment_status'], subtotal=subtotal, discount=discount,
                  shipping=shipping, total=subtotal - discount + shipping,
                  items=[dict(item) for item in order['items']])
    if result['status'] == 'paid':
        for item in result['items']:
            products[item['product_id']]['stock'] -= item['quantity']
    return result


def generate_customer_report(processed_orders):
    paid = [order for order in processed_orders if order['status'] == 'paid']
    customers = {order['customer'] for order in paid}
    # LEGB: customer_revenue closes over the enclosing function's local paid list.
    def customer_revenue(customer):
        return sum_amounts(*(order['total'] for order in paid if order['customer'] == customer))
    revenue = {customer: customer_revenue(customer) for customer in customers}
    ranked = sorted(revenue, key=lambda customer: (-revenue[customer], customer))
    return {'revenue': revenue,
            'top_customers': [name for name in ranked if revenue[name] == revenue[ranked[0]]]}


def generate_product_report(processed_orders, products, low_stock_threshold=5):
    quantities = {}
    for order in processed_orders:
        if order['status'] == 'paid':
            for item in order['items']:
                product_id = item['product_id']
                quantities[product_id] = quantities.get(product_id, 0) + item['quantity']
    ranked = sorted(quantities, key=lambda product_id: (-quantities[product_id], product_id))
    return {
        'quantities': quantities,
        'top_products': [pid for pid in ranked if quantities[pid] == quantities[ranked[0]]],
        'low_stock': sorted(pid for pid, product in products.items()
                            if product['stock'] <= low_stock_threshold),
        'categories': sorted({product['category'] for product in products.values()}),
    }


def generate_sales_report(processed_orders, products, low_stock_threshold=5):
    paid = [order for order in processed_orders if order['status'] == 'paid']
    return {
        'total_orders': len(processed_orders),
        **{f'{status}_orders': sum(order['status'] == status for order in processed_orders)
           for status in ('paid', 'pending', 'rejected')},
        'total_revenue': sum_amounts(*(order['total'] for order in paid)),
        'total_discount': sum_amounts(*(order['discount'] for order in paid)),
        'total_shipping': sum_amounts(*(order['shipping'] for order in paid)),
        'customers': generate_customer_report(processed_orders),
        'products': generate_product_report(processed_orders, products, low_stock_threshold),
    }


def format_sales_report(report, products):
    lines = ['========== SALES REPORT ==========']
    for key in ('total_orders', 'paid_orders', 'pending_orders', 'rejected_orders'):
        lines.append(f"{key.replace('_', ' ').title()}: {report[key]}")
    for key in ('total_revenue', 'total_discount', 'total_shipping'):
        lines.append(f"{key.replace('_', ' ').title()}: ${report[key]:.2f}")
    lines.append('Top Customer: ' + (', '.join(report['customers']['top_customers']) or 'None'))
    lines.append('Top Selling Product: ' + (', '.join(products[pid]['name'] + f' ({pid})'
                 for pid in report['products']['top_products']) or 'None'))
    lines.append('Low Stock Products:')
    lines.extend([f"- {products[pid]['name']} ({pid}): {products[pid]['stock']}"
                  for pid in report['products']['low_stock']] or ['- None'])
    return '\n'.join(lines + ['=================================='])


def starter_data():
    """Return fresh dictionaries so repeated demo runs do not share inventory."""
    products = {
        'P001': {'name': 'Laptop', 'price': 1200, 'category': 'Electronics', 'stock': 10},
        'P002': {'name': 'Mouse', 'price': 25, 'category': 'Accessories', 'stock': 50},
        'P003': {'name': 'Keyboard', 'price': 75, 'category': 'Accessories', 'stock': 20},
        'P004': {'name': 'Monitor', 'price': 300, 'category': 'Electronics', 'stock': 15},
    }
    orders = [
        {'order_id': 'ORD001', 'customer': 'Ali', 'items': [
            {'product_id': 'P001', 'quantity': 1}, {'product_id': 'P002', 'quantity': 2}], 'payment_status': 'paid'},
        {'order_id': 'ORD002', 'customer': 'Ahmed', 'items': [
            {'product_id': 'P003', 'quantity': 2}, {'product_id': 'P004', 'quantity': 1}], 'payment_status': 'paid'},
        {'order_id': 'ORD003', 'customer': 'Ali', 'items': [
            {'product_id': 'P002', 'quantity': 5}], 'payment_status': 'pending'},
    ]
    return products, orders


if __name__ == '__main__':
    inventory, orders = starter_data()
    processed = [process_order(order, inventory) for order in orders]
    print(format_sales_report(generate_sales_report(processed, inventory), inventory))
