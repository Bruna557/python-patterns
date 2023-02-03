from __future__ import annotations
from dataclasses import dataclass
from datetime import date
from typing import Optional, List, Set


class OutOfStock(Exception):
    pass

# A standalone function for our domain service
def allocate(line: OrderLine, batches: List[Batch]) -> str:
    try:
        batch = next(
            b for b in sorted(batches) if b.can_allocate(line)
        )
        batch.allocate(line)
        return batch.reference
    except StopIteration:
        raise OutOfStock(f'Out of stock for sku {line.sku}')


'''
The dataclass decorator will add dunder methods to the class (__init__,
__repr__, __eq__, __hash__).
If frozen is True, assigning to fields will generate an exception.

A value object is any domain object that is uniquely identified by the data it
holds; we usually make them immutable. Two lines with the same orderid, sku,
and qty are equal.
'''
@dataclass(frozen=True)
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

    @property
    def allocated_quantity(self) -> int:
        return sum(line.qty for line in self._allocations)

    @property
    def available_quantity(self) -> int:
        return self._purchased_quantity - self.allocated_quantity
