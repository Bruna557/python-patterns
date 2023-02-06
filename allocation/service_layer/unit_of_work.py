# pylint: disable=attribute-defined-outside-init
from __future__ import annotations
import abc
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session

from allocation import config
from allocation.adapters import repository


class AbstractUnitOfWork(abc.ABC):
    products: repository.AbstractProductRepository

    def __enter__(self) -> AbstractUnitOfWork: # executed when we enter the with block
        return self

    def __exit__(self, *args): # executed when we exit the with block
        self.rollback()

    @abc.abstractmethod
    def commit(self):
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

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()
