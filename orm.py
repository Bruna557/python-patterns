from sqlalchemy import Table, MetaData, Column, Integer, String, Date, ForeignKey
from sqlalchemy.orm import relationship, registry

import model


'''
Classic SQLAlchemy would have the model depending on the ORM:

    class OrderLine(Base):
        id = Column(Integer, primary_key=True)

Here we invert the dependency and make the ORM depend on the model;
we define the schema separately and define and explicit mapper for
how to convert between the schema and our domain model.
The end result will be that, if we call start_mappers, we will be able to
easily load and save domain model instances from and to the database.
'''

metadata = MetaData()

order_lines = Table(
    "order_lines",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("sku", String(255)),
    Column("qty", Integer, nullable=False),
    Column("orderid", String(255)),
)

batches = Table(
    "batches",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("reference", String(255)),
    Column("sku", String(255)),
    Column("_purchased_quantity", Integer, nullable=False),
    Column("eta", Date, nullable=True),
)

allocations = Table(
    "allocations",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("orderline_id", ForeignKey("order_lines.id")),
    Column("batch_id", ForeignKey("batches.id")),
)


def start_mappers():
    mapper_reg = registry()
    lines_mapper = mapper_reg.map_imperatively(model.OrderLine, order_lines)
    mapper_reg.map_imperatively(
        model.Batch,
        batches,
        properties={
            "_allocations": relationship(
                lines_mapper, secondary=allocations, collection_class=set,
            )
        },
    )
