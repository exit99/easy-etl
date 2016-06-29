import pytest
from random import randint

import dataset

from easy_etl import ETLProcess

NAMES = ["Joe", "John", "Mary", "Lila", "Tom"]


@pytest.yield_fixture(scope="function")
def dbs(request):
    """Connected ETLProcess object that clears the database after each test."""
    dummy_data = [{
        "name": NAMES[randint(0, len(NAMES)-1)],
        "age": randint(1, 99),
        "last_name": NAMES[randint(0, len(NAMES)-1)],
    } for i in range(0, 3)]
    dbs = (dataset.connect("mysql+mysqldb://test@127.0.0.1:3306/src"),
           dataset.connect("mysql+mysqldb://test@127.0.0.1:3306/target"))
    dbs[0]['mytable'].insert_many(dummy_data)
    yield dbs
    for db in dbs:
        for table in db.tables:
            db[table].drop()


@pytest.fixture
def process(dbs):
    return ETLProcess(dbs[0], dbs[1], "mytable")
