# pylint: disable=attribute-defined-outside-init
from __future__ import annotations
import abc
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session


from allocation import config
from allocation.adapters import repository
from . import messagebus


class AbstractUnitOfWork(abc.ABC):
    products: repository.AbstractProductRepository

    # executed when we enter the with block
    def __enter__(self) -> AbstractUnitOfWork:
        return self

    # executed when we exit the with block
    def __exit__(self, *args):
        self.rollback()

    def commit(self):
        self._commit()

    '''
    After committing, we run through all the objects that our repository has
    seen and pass their events to the message bus.
    '''
    def collect_new_events(self):
        for product in self.products.seen:
            while product.events:
                yield product.events.pop(0)

    @abc.abstractmethod
    def _commit(self):
        raise NotImplementedError

    '''
    If we don't commit, or if we exit the context manager by raising an error,
    we do a rollback. The rollback has no effect if commit() has been called
    '''
    @abc.abstractmethod
    def rollback(self):
        raise NotImplementedError


DEFAULT_SESSION_FACTORY = sessionmaker(
    bind=create_engine(
        config.get_postgres_uri(),
    )
)


class SqlAlchemyUnitOfWork(AbstractUnitOfWork):
    def __init__(self, session_factory=DEFAULT_SESSION_FACTORY):
        self.session_factory = session_factory

    def __enter__(self):
        self.session = self.session_factory()  # type: Session
        self.products = repository.SqlAlchemyRepository(self.session)
        return super().__enter__()

    def __exit__(self, *args):
        super().__exit__(*args)
        self.session.close()

    def _commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()
