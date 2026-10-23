"""Run the function-based regression suite with python3 test_backend.py."""
from copy import deepcopy
from backend import (starter_data, process_order, calculate_discount, calculate_shipping,
                     generate_sales_report, format_sales_report, money)


def example_order(**changes):
    order = {'order_id': 'T1', 'customer': 'Ali', 'payment_status': 'paid',
             'items': [{'product_id': 'P002', 'quantity': 1}]}
    order.update(changes)
    return order


def test_starter_report():
    products, orders = starter_data()
    results = [process_order(order, products) for order in orders]
    report = generate_sales_report(results, products)
    assert [report[key] for key in ('total_orders', 'paid_orders', 'pending_orders', 'rejected_orders')] == [3, 2, 1, 0]
    assert report['total_revenue'] == money('1510')
    assert report['total_discount'] == money('210')
    assert report['total_shipping'] == money('20')
    assert report['customers']['top_customers'] == ['Ali']
    assert report['products']['top_products'] == ['P002', 'P003']
    assert {pid: p['stock'] for pid, p in products.items()} == {'P001': 9, 'P002': 48, 'P003': 18, 'P004': 14}
    assert '$1510.00' in format_sales_report(report, products)


def test_invalid_orders_are_atomic():
    invalid = [None, [], {}, example_order(items=[]), example_order(items=None),
               example_order(payment_status='failed'), example_order(customer=''),
               example_order(items=[None]), example_order(items=[{'product_id': []}])]
    for pid, quantity in [('unknown', 1), ('P002', 0), ('P002', -1), ('P002', 51),
                          ('P002', True), ('P002', 1.5), ('P002', '1')]:
        invalid.append(example_order(items=[{'product_id': pid, 'quantity': quantity}]))
    invalid.append(example_order(items=[{'product_id': 'P002', 'quantity': 30}] * 2))
    invalid.append(example_order(items=[{'product_id': 'P002', 'quantity': 1},
                                       {'product_id': 'unknown', 'quantity': 1}]))
    for order in invalid:
        products, _ = starter_data()
        before = deepcopy(products)
        result = process_order(order, products)
        assert result['status'] == 'rejected' and result['errors'], order
        assert result['total'] == 0 and products == before
    assert process_order(example_order(), {})['status'] == 'rejected'


def test_pending_and_options():
    products, _ = starter_data()
    before = deepcopy(products)
    pending = process_order(example_order(payment_status='pending'), products)
    assert pending['status'] == 'pending' and products == before
    report = generate_sales_report([pending], products)
    assert report['total_revenue'] == report['total_discount'] == report['total_shipping'] == 0
    order = example_order(items=[{'product_id': 'P004', 'quantity': 1}])
    result = process_order(order, products, include_shipping=False, apply_discount=False)
    assert result['total'] == 300 and result['discount'] == result['shipping'] == 0
    assert order['items'][0]['quantity'] == 1
    result['items'][0]['quantity'] = 999
    assert order['items'][0]['quantity'] == 1
    for options in ({'unknown': True}, {'include_shipping': 'false'}):
        try:
            process_order(order, products, **options)
        except ValueError:
            pass
        else:
            raise AssertionError('Invalid options were accepted')


def test_discount_and_shipping_boundaries():
    for subtotal, discount, shipping in [('0', '0', '20'), ('199.99', '0', '20'),
        ('200', '10', '20'), ('499.99', '25', '20'), ('500', '50', '0'),
        ('999.99', '100', '0'), ('1000', '150', '0')]:
        assert calculate_discount(money(subtotal)) == money(discount)
        assert calculate_shipping(money(subtotal)) == money(shipping)


def test_reports_empty_low_stock_and_ties():
    report = generate_sales_report([], {})
    assert report['total_orders'] == 0 and report['total_revenue'] == 0
    assert report['customers']['top_customers'] == []
    assert report['products']['top_products'] == report['products']['low_stock'] == []
    assert 'Top Customer: None' in format_sales_report(report, {})
    products, _ = starter_data()
    assert generate_sales_report([], products)['products']['low_stock'] == []
    products['P002']['stock'] = 5
    assert generate_sales_report([], products)['products']['low_stock'] == ['P002']
    results = [process_order(example_order(customer=name), products) for name in ('Ali', 'Ali', 'Zara', 'Zara')]
    report = generate_sales_report(results, products)
    assert report['customers']['top_customers'] == ['Ali', 'Zara']
    assert report['customers']['revenue']['Ali'] == 90
    assert report['products']['quantities']['P002'] == 4
    assert report['products']['categories'] == ['Accessories', 'Electronics']


def test_sequential_stock_and_duplicate_lines():
    products, _ = starter_data()
    products['P002']['stock'] = 3
    order = example_order(items=[{'product_id': 'P002', 'quantity': 1}, {'product_id': 'P002', 'quantity': 2}])
    assert process_order(order, products)['total'] == 95
    assert products['P002']['stock'] == 0
    assert process_order(example_order(), products)['status'] == 'rejected'


if __name__ == '__main__':
    tests = sorted((name, value) for name, value in list(globals().items()) if name.startswith('test_'))
    for name, test in tests:
        test()
        print(f'PASS {name}')
    print(f'{len(tests)} test groups passed')
