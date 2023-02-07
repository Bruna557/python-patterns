# Example application code for the python architecture book

A product is identified by a SKU, pronounced "skew," which is short for stock-keeping unit. Customers place orders. An order is identified by an order reference and comprises multiple order lines, where each line has a SKU and a quantity.

The purchasing department orders small batches of stock. A batch of stock has a unique ID called a reference, a SKU, and a quantity.

We need to allocate order lines to batches. When we've allocated an order line to a batch, we will send stock from that specific batch to the customer's delivery address. When we allocate x units of stock to a batch, the available quantity is reduced by x.

We can't allocate to a batch if the available quantity is less than the quantity of the order line. Batches have an ETA if they are currently shipping, or they may be in warehouse stock. We allocate to warehouse stock in preference to shipment batches. We allocate to shipment batches in order of which has the earliest ETA.

## Run tests
```bash
pytest
```

## Database setup
psql -U postgres
CREATE ROLE allocation LOGIN PASSWORD '1234' NOINHERIT CREATEDB;
CREATE DATABASE allocation
\connect allocation

CREATE TABLE products (sku VARCHAR PRIMARY KEY, version_number INTEGER DEFAULT '0' NOT NULL);
CREATE TABLE batches(id SERIAL PRIMARY KEY, reference VARCHAR, sku VARCHAR, _purchased_quantity INTEGER, eta DATE, FOREIGN KEY (sku) REFERENCES products(sku));
CREATE TABLE order_lines(id SERIAL PRIMARY KEY, sku VARCHAR, qty INTEGER, orderid VARCHAR);
CREATE TABLE allocations(id SERIAL PRIMARY KEY, orderline_id INTEGER, batch_id INTEGER, FOREIGN KEY (orderline_id) REFERENCES order_lines(id), FOREIGN KEY (batch_id) REFERENCES batches(id));

INSERT INTO batches (reference, sku, _purchased_quantity, eta) VALUES ('123', 'SMALL-TABLE', 20, null);

GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO allocation;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO allocation;

## Run app
export FLASK_APP=allocation/entrypoints/flask_app.py
export FLASK_DEBUG=1
export PYTHONUNBUFFERED=1
flask run --host=0.0.0.0 --port=5005

## Testing
curl --location --request POST 'http://127.0.0.1:5005/batches' \
--header 'Content-Type: application/json' \
--data-raw '{
    "ref": "321",
    "sku": "COMPLICATED-LAMP",
    "qty": 17,
    "eta": "2023-02-04"
}'

curl --location --request POST 'http://127.0.0.1:5005/allocate' \
--header 'Content-Type: application/json' \
--data-raw '{
    "orderid": "321",
    "sku": "COMPLICATED-LAMP",
    "qty": 5
}'

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
- Our Flask API endpoints become very thin and easy to write: their only responsibility is doing "web stuff," such as parsing JSON and producing the right HTTP codes for happy or unhappy cases;
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

Most of the time, when we are adding a new feature or fixing a bug, we don't need to make extensive changes to the domain model. In these cases, we prefer to write tests against services because of the lower coupling and higher coverage. When starting a new project or when hitting a particularly gnarly problem, we will drop back down to writing tests against the domain model so we get better feedback and executable documentation of our intent.

### 6 - Unit of Work
The Unit of Work (UoW) pattern is an abstraction around data integrity. Each unit of work represents an atomic update. It will allow us to finally and fully decouple our service layer from the data layer.
We implemented the UoW class using Python Context Manager; the with keyword is used.

### 7 - Aggregate
Read chapter 7:
- Invariants, Constraints, and Consistency
- What Is an Aggregate?

The Product we define here might not look like what you'd expect a Product model to look like. No price, no description, no dimensions. Our allocation service doesn't care about any of those things. This is the power of bounded contexts; the concept of a product in one app can be very different from another. Rather than trying to build a single model (or class, or database) to capture all the use cases, it's better to have several models, draw boundaries around each context, and handle the translation between different contexts explicitly.

Once you define certain entities to be aggregates, we need to apply the rule that they are the only entities that are publicly accessible to the outside world. In other words, the only repositories we are allowed should be repositories that return aggregates.

### 8 - Events and the Message Bus
When we can't allocate an order because we're out of stock, we should alert the buying team by sending an email. Where to put this logic?
We don't want our model to have any dependencies on infrastructure concerns like email.send_mail. In the service layer, it violates the SRP (allocate_and_send_mail_if_out_of_stock). To solve this problem we're going to introduce the patterns Domain Events and the Message Bus.

- Rather than being concerned about emails, our model will be in charge of recording events.
- An event is a kind of value object. Events don't have any behavior, because they're pure data structures.
- A message bus basically says, "When I see this event, I should invoke the following handler function." In other words, it's a simple publish-subscribe system. Handlers are subscribed to receive events, which we publish to the bus.

Pros:
- A message bus gives us a nice way to separate responsibilities when we have to take multiple actions in response to a request.
- Event handlers are nicely decoupled from the "core" application logic, making it easy to change their implementation later.

Cons:
- The message bus is an additional thing to wrap your head around; the implementation in which the unit of work raises events for us is neat but also magic. It's not obvious when we call commit that we're also going to go and send email to people.
- What's more, that hidden event-handling code executes synchronously, meaning your service-layer function doesn't finish until all the handlers for any events are finished. That could cause unexpected performance problems in your web endpoints (adding asynchronous processing is possible but makes things even more confusing).
- More generally, event-driven workflows can be confusing because after things are split across a chain of multiple handlers, there is no single place in the system where you can understand how a request will be fulfilled.

### Message Bus
An event we'll call BatchQuantityChanged should lead us to change the quantity on the batch and also to apply a business rule: if the new quantity drops to less than the total already allocated, we need to deallocate those orders from that batch. Then each one will require a new allocation, which we can capture as an event called AllocationRequired.

#### Architecture Change: Everything Will Be an Event Handler
- services.allocate() will be the handler for an AllocationRequired event and could emit Allocated events as its
output.
- services.add_batch() could be the handler for a BatchCreated event.
- An event called BatchQuantityChanged can invoke a handler called change_batch_quantity().
- And the new AllocationRequired events that it may raise can be passed on to services.allocate() too, so there is no conceptual difference between a brand-new allocation coming from the API and a reallocation that’s internally triggered by a deallocation.

### Epilogue
Aggregates are a consistency boundary. In general, each use case should update a single aggregate at a time. One handler fetches one aggregate from a repository, modifies its state, and raises any events that happen as a result. If you need data from another part of the system, it's totally fine to use a read model, but avoid updating multiple aggregates in a single transaction.
