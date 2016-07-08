import pytest
import os

from easy_etl import ETLProcess


@pytest.mark.parametrize("sql,", [
    "SELECT name FROM mytable;",
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "test.sql")
])
def test_extract(process, sql):
    process.extract(sql)
    process.load()
    data = [i for i in process.write_db[process.write_table_name].all()]
    assert len(data) == len([i for i in process.read_db["mytable"].all()])
    assert process.write_db[process.write_table_name].columns == ["id", "name"]


def test_extract_override(process):
    def extract():
        return [{"test": "value"} for i in range(0, 3)]

    process.extract_override(extract)
    process.load()
    data = [i for i in process.write_db[process.write_table_name].all()]
    assert len(data) == 3
    assert len(data[0]) == 2
    for row in data:
        assert row["test"] == "value"


def test_middleware(process):
    def add_column(results):
        new_results = []
        for row in results:
            row["extra"] = True
            new_results.append(row)
        return new_results

    process.extract("SELECT name FROM mytable;")
    process.middleware(add_column)
    process.load()
    data = [i for i in process.write_db[process.write_table_name].all()]
    for row in data:
        assert row.keys() == ["id", "name", "extra"]


def test_transform(process):
    process.extract("SELECT name, last_name FROM mytable;")
    process.transform("name", "last_name").upper()
    process.load()
    data = [i for i in process.write_db[process.write_table_name].all()]
    assert len(data) == len([i for i in process.read_db["mytable"].all()])
    for row in data:
        row.pop('id')
        for v in row.values():
            assert v.upper() == v


def test_transform_chaining(process):
    process.extract("SELECT name, last_name FROM mytable;")
    process.transform("name", "last_name").upper().lower()
    process.load()
    data = [i for i in process.write_db[process.write_table_name].all()]
    assert len(data) == len([i for i in process.read_db["mytable"].all()])
    for row in data:
        row.pop('id')
        for v in row.values():
            assert v.lower() == v


def test_ignore(process):
    process.extract("SELECT name, last_name FROM mytable;")
    process.ignore("last_name")
    process.load()
    data = [i for i in process.write_db[process.write_table_name].all()]
    assert len(data) == len([i for i in process.read_db["mytable"].all()])
    for row in data:
        assert row.keys() == ["id", "name"]


@pytest.mark.parametrize("safe,answ", [
    (False, ["id", "name"]),
    (True, ["id", "name", "last_name"]),
])
def test_drop_columns(process, safe, answ):
    process.extract("SELECT name, last_name FROM mytable;")
    process.load()

    process.extract("SELECT name, last_name FROM mytable;")
    process.ignore("last_name")
    process.load(safe=safe)

    assert process.write_db[process.write_table_name].columns == answ


def test_load(process):
    for i in range(0, 2):
        process.extract("SELECT name FROM mytable;")
        process.load()

    data = [i for i in process.write_db[process.write_table_name].all()]
    assert len(data) == 6


def test_load_upsert(process):
    process.extract("SELECT name, last_name FROM mytable;")
    process.load()

    process.extract("SELECT name, last_name FROM mytable;")
    process.transform("last_name").upper()
    process.load(upsert_fields=["name"])

    data = [i for i in process.write_db[process.write_table_name].all()]
    assert len(data) == 3
    for row in data:
        assert row["last_name"] == row["last_name"].upper()


def test_link(process):
    def increment(results):
        new_results = []
        for i, row in enumerate(results):
            row['i'] = i + 4
            new_results.append(row)
        return new_results

    process.write_table_name = "dimension"
    process.extract("SELECT name, last_name FROM mytable;")
    process.middleware(increment)
    process.load()

    process.extract("SELECT name, last_name FROM mytable;")
    process.middleware(increment)
    process.link("i", "dimension", "i", name="my_i")
    process.load(upsert_fields=['i'])

    data = [i for i in process.write_db[process.write_table_name].all()]
    for i, row in enumerate(data):
        assert row['my_i'] == str(i + 1)


def test_link_closest(process):
    def func(rate):
        def increment(results):
            new_results = []
            for i, row in enumerate(results):
                row['i'] = i + rate
                new_results.append(row)
            return new_results
        return increment

    process.write_table_name = "dimension"
    process.extract("SELECT name, last_name FROM mytable;")
    process.middleware(func(3))
    process.load()

    process.extract("SELECT name, last_name FROM mytable;")
    process.middleware(func(2))
    process.link_closest("i", "dimension", "i", name="my_i")
    process.load(upsert_fields=['i'])

    data = [i for i in process.write_db[process.write_table_name].all()]
    assert [i['my_i'] for i in data] == ['1', '2', None, '1']


def test_type(process):
    t = float
    process.extract("SELECT age FROM mytable;", types={"age": t})
    process.load()
    data = [i for i in process.write_db[process.write_table_name].all()]
    for i in data:
        assert type(i['age']) is t
