from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Optional, List, Set
from . import commands, events


class OutOfStock(Exception):
    pass


class Product:
    def __init__(self, sku: str, batches: List[Batch], version_number: int = 0):
        self.sku = sku
        self.batches = batches
        self.version_number = version_number
        self.events = [] # type: List[events.Event]

    def allocate(self, line: OrderLine) -> str:
        try:
            batch = next(b for b in sorted(self.batches) if b.can_allocate(line))
            batch.allocate(line)
            self.version_number += 1
            self.events.append(
                events.Allocated(
                    orderid=line.orderid,
                    sku=line.sku,
                    qty=line.qty,
                    batchref=batch.reference,
                )
            )
            return batch.reference
        except StopIteration:
            self.events.append(events.OutOfStock(line.sku))
            return None

    def change_batch_quantity(self, ref: str, qty: int):
        batch = next(b for b in self.batches if b.reference == ref)
        batch._purchased_quantity = qty
        while batch.available_quantity < 0:
            line = batch.deallocate_one()
            self.events.append(
                commands.Allocate(line.orderid, line.sku, line.qty)
            )


'''
The dataclass decorator will add dunder methods to the class (__init__,
__repr__, __eq__, __hash__).

A value object is any domain object that is uniquely identified by the data it
holds; we usually make them immutable. Two lines with the same orderid, sku,
and qty are equal.
'''
@dataclass(unsafe_hash=True)
class OrderLine:
    orderid: str
    sku: str
    qty: int


'''
Entities, unlike values, have identity equality. We can change their values,
and they are still recognizably the same thing. A Batch is identified by a
reference; we can allocate lines or change the date that we expect it to
arrive, and it will still be the same entity.

We usually make this explicit in code by implementing equality operators.
'''
class Batch:
    def __init__(self, ref: str, sku: str, qty: int, eta: Optional[date]):
        self.reference = ref
        self.sku = sku
        self.eta = eta
        self._purchased_quantity = qty
        self._allocations = set() # type: Set[OrderLine]

    def __repr__(self):
        return f"<Batch {self.reference}>"

    def __eq__(self, other): # defines the behavior of the == operator
        if not isinstance(other, Batch):
            return False
        return other.reference == self.reference

    def __hash__(self): # controls the behavior of objects when you add them to sets or use them as dict keys
        return hash(self.reference)

    def __gt__(self, other): # allows us to use sorted
        if self.eta is None:
            return False
        if other.eta is None:
            return True
        return self.eta > other.eta

    def can_allocate(self, line: OrderLine):
        return self.sku == line.sku and self.available_quantity >= line.qty

    def allocate(self, line: OrderLine):
        if self.can_allocate(line):
            self._allocations.add(line)

    def deallocate(self, line: OrderLine):
        if line in self._allocations:
            self._allocations.remove(line)

    def deallocate_one(self) -> OrderLine:
        return self._allocations.pop()

    @property
    def allocated_quantity(self) -> int:
        return sum(line.qty for line in self._allocations)

    @property
    def available_quantity(self) -> int:
        return self._purchased_quantity - self.allocated_quantity
