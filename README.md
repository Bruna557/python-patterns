# Example application code for the python architecture book

A product is identified by a SKU, pronounced “skew,” which is short for stock-keeping unit. Customers place orders. An order is identified by an order reference and comprises multiple order lines, where each line has a SKU and a quantity.

The purchasing department orders small batches of stock. A batch of stock has a unique ID called a reference, a SKU, and a quantity.

We need to allocate order lines to batches. When we've allocated an order line to a batch, we will send stock from that specific batch to the customer's delivery address. When we allocate x units of stock to a batch, the available quantity is reduced by x.

We can't allocate to a batch if the available quantity is less than the quantity of the order line. Batches have an ETA if they are currently shipping, or they may be in warehouse stock. We allocate to warehouse stock in preference to shipment batches. We allocate to shipment batches in order of which has the earliest ETA.

## Run tests
```bash
pytest
```

## Database setup
psql -U postgres
\connect allocation

CREATE TABLE batches(id SERIAL PRIMARY KEY, reference VARCHAR, sku VARCHAR, _purchased_quantity INTEGER, eta DATE);
CREATE TABLE order_lines(id SERIAL PRIMARY KEY, sku VARCHAR, qty INTEGER, orderid VARCHAR);
CREATE TABLE allocations(id SERIAL PRIMARY KEY, orderline_id INTEGER, batch_id INTEGER, FOREIGN KEY (orderline_id) REFERENCES order_lines(id), FOREIGN KEY (batch_id) REFERENCES batches(id));

INSERT INTO batches (reference, sku, _purchased_quantity, eta) VALUES ('123', 'SMALL-TABLE', 20, null);

GRANT SELECT ON ALL TABLES IN SCHEMA public TO allocation;
GRANT INSERT ON ALL TABLES IN SCHEMA public TO allocation;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO allocation;

## Run app
FLASK_APP=flask_app.py
FLASK_DEBUG=1
PYTHONUNBUFFERED=1
flask run --host=0.0.0.0 --port=5005

## Patterns
### Repository
The Repository pattern is an abstraction over persistent storage. It hides the boring details of data access by pretending that all of our data is in memory.
It also makes it easy to create a FakeRepository for testing.

### Service layer
By adding a service layer
- Our Flask API endpoints become very thin and easy to write: their only responsibility is doing “web stuff,” such as parsing JSON and producing the right HTTP codes for happy or unhappy cases.
- We have a single place to capture all the use cases for our application.
