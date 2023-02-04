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
export FLASK_APP=entrypoints/flask_app.py
export FLASK_DEBUG=1
export PYTHONUNBUFFERED=1
flask run --host=0.0.0.0 --port=5005

## Chapters
### 2 - Repository Pattern
The Repository pattern is an abstraction over persistent storage. It hides the boring details of data access by pretending that all of our data is in memory.
It also makes it easy to create a FakeRepository for testing.

#### Dependency Inversion
Classic SQLAlchemy would have the model depending on the ORM:

    class OrderLine(Base):
        id = Column(Integer, primary_key=True)

Here we invert the dependency and make the ORM depend on the model; we define the schema separately (orm.py) and define and explicit mapper for
how to convert between the schema and our domain model. The end result will be that, if we call start_mappers, we will be able to easily load and save domain model instances from and to the database.

### 4 - Service Layer
By adding a service layer
- Our Flask API endpoints become very thin and easy to write: their only responsibility is doing “web stuff,” such as parsing JSON and producing the right HTTP codes for happy or unhappy cases;
- We have a single place to capture all the use cases for our application.

Cons:
- If your app is purely a web app, your controllers/view functions can be the single place to capture all the use cases;
- Putting too much logic into the service layer can lead to the Anemic Domain anti-pattern; you can get a lot of the benefits that come from having rich domain models by simply pushing logic out of your controllers and down to the model layer, without needing to add an extra layer in between

#### Ports and Adapters
Ports and adapters came out of the OO world, and the definition we hold onto is that the port is the interface between our application and whatever it is we wish to abstract away, and the adapter is the implementation behind that interface or abstraction.

Concretely, AbstractRepository is a port, and SqlAlchemyRepository and FakeRepository are the adapters. Entrypoints are adapters too.

### 5 - TDD in High Gear and Low Gear
Every line of code that we put in a test is like a blob of glue, holding the system in a particular shape. The more low-level tests we have, the harder it will be to change things.
Tests are supposed to help us change our system fearlessly, but often we see teams writing too many tests against their domain model. This causes problems when they come to change their codebase and find that they need to update tens or even hundreds of unit tests.

Most of the time, when we are adding a new feature or fixing a bug, we don’t need to make extensive changes to the domain model. In these cases, we prefer to write tests against services because of the lower coupling and higher coverage. When starting a new project or when hitting a particularly gnarly problem, we will drop back down to writing tests against the domain model so we get better feedback and executable documentation of our intent.
