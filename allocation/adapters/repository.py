import abc
from allocation.domain import model


# abc = absctract base class
class AbstractRepository(abc.ABC):
    '''
    Python will not let you instantiate a class that doesn't implement
    all the abstractmethod defined in its parent class
    '''
    @abc.abstractmethod
    def add(self, product: model.Product):
        raise NotImplementedError

    @abc.abstractmethod
    def get(self, sku) -> model.Product:
        raise NotImplementedError


class SqlAlchemyRepository(AbstractRepository):
    def __init__(self, session):
        self.session = session

    def add(self, product):
        self.session.add(product)

    def get(self, sku):
        return self.session.query(model.Product).filter_by(sku=sku).first()
