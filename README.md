# Python order-processing backend

A solved, function-based implementation of `Python_Intern_Real_World_Assessment.docx`.
Uses Python 3.10+ and the standard library. No installation, database, web server,
classes, or third-party packages are required.

## Run

From the repository directory:

```sh
python3 backend.py
python3 test_backend.py
```

The demo processes the document's three orders and prints a sales report:
2 paid, 1 pending, 0 rejected; revenue **$1,510.00**, discounts **$210.00**,
and shipping **$20.00**. Ali is the top customer; Mouse and Keyboard tie for
most units sold. The test command exits with an error if any assertion fails.

## Use in Python

```python
from backend import process_order, generate_sales_report, starter_data

products, orders = starter_data()
processed = [process_order(order, products) for order in orders]
report = generate_sales_report(processed, products)
```

`process_order(order, products, include_shipping=True, apply_discount=True)`
returns a result dictionary containing status, validation errors, copied items,
subtotal, discount, shipping, and total. Only a valid paid order reduces stock.
Process orders sequentially against the same inventory. This is an in-memory
exercise: it does not provide persistence, concurrent stock updates, or duplicate
order-ID detection; submitting an order twice processes it twice.

## Business rules and choices

- Quantities must be positive integers (booleans are rejected). Repeated product
  lines are combined for stock validation. Invalid orders leave all stock intact.
- Product records are trusted catalog data with name, nonnegative price,
  category, and nonnegative integer stock. Order IDs and customers must be
  nonempty strings; payment status must be exactly `paid` or `pending`.
- Discounts and free-shipping eligibility use the original subtotal.
- Currency uses standard-library `Decimal`, rounding half up to cents.
- Revenue includes discounted merchandise plus collected shipping. Pending
  orders retain their calculated quote but contribute nothing to report totals.
- Customer ranking uses paid revenue; product ranking uses paid units sold.
  All tied leaders are reported in alphabetical customer/product-ID order.
- Low stock means **5 units or fewer**, configurable with `low_stock_threshold`.
- Empty reports display `None` for leaders and low-stock products.
- The backend demonstrates `*args`, configurable `**kwargs`, lambda sorting,
  comprehensions, sets, and a documented closure illustrating LEGB scope.

The regression suite covers the starter report, malformed orders, all required
edge cases, discount/shipping boundaries, pending orders, options, ties, repeated
product lines, sequential stock exhaustion, and inventory mutation safety.
