# easy-etl

Not all ETL processes need complicated task managment and streaming functionality.  

Easy-etl is a simple, no frills, etl package to make transforming small to medium sized database entries into data cubes easy.
It was made to power a majority of the ETL processes in the datawarehouse at Hivelocity.

In majority of ETL processes many of the same techniques are used to process the data, such as linking fact and dimension tables.
Easy-etl abstracts these processes into a simple `ETLProcess` class which allows developrs to avoid wrting the same code for 
a majority of their ETL processes.

Easy-etl is powered by the `dataset` python package (which is powered my `sqlalchemy`) and the `ETLProcess` class requries
dataset connections to your source and target databases.

Easy-etl is a pipeline. The `extract` and `transform` functions called on the `ETLProcess` stage tasks in the pipeline. 
The pipeline is executed on the `load` call.

*"Any processing that can be done on the SQL level, should be done at the SQL level." - easy-etl philosophy*


## Quickstart

`pip install easy-etl`

```python
import dataset
from easy_etl import ETLProcess

src_db = dataset.connect("sqlite:///src.db")
target_db = dataset.connect("sqlite:///target.db")

process = ETLProcess(src_db, target_db, "target_tablename")
process.extract("query.sql")  
process.transform("name").default("Unknown")  
process.transform("state", "country").upper()  
process.load()
```

## Extracting Data

The `extract` function can accept either the path of a sql file or a string of a sql command.
It always reads from the `src_db` passed to the `ETLProcess` on initialization.
**Only the sql from the most recent extract call will be called when the process is executed.**

### Extracting with SQL file

`process.extract("path/to/file/file.sql")`

### Extracting with SQL string

`process.extract("SELECT * FROM t1 INNER JOIN t2 ON t1.field t2.field")`

### Overriding the extract method

Sometimes the needed data cannot be exteracted with SQL alone.  In this case you can pass
your own function to the etl process to be run on the load instead of using the `extract` function.
**Your extract function must return a list of dictionaries**

```python
def custom_extract():
    return [{"col1": random.randint(0, 10)} for i in range(0, 100)]

process.extract_override(custom_extract)
```

### Type conversions

By default all types will be strings.  To force a type conversion pass the column name
along with the desired type in a dictionary via the types kwarg.

`process.extract(sql, types={"column1": float, "column2": int})`


### Formatting extracted data with middleware

Sometimes the data returned by the extract function isn't in the exact format we need.
It may even need to be combined with data from another ETL process.  This is easy enough to accomplish
by using middleware functions.  Middleware functions are executed in the order they are added and are 
executed in between the extract and transform functions.
*You function must accept a list of dicts (representing a row) and return a list of dicts*

```python
def add_some_data(results):
    new_results = []
    for row in results:
        if row['field1'] == "yes" and row['field2'] == "yes":
            row['outlook'] = "is positive"
        else:
            row['outlook'] = "is negative"
        new_results.append(row)
    return new_results

process.middleware(add_some_data)
```

### Controlling field names

According to Kimball columns of tables in a data cube should be human readable to make it easier for analysts.
Keeping with the easy-etl motto, this can and should be accomplished in the SQL.

Assuming a column named `litv_of_cst` this can be renamed in the SQL file to `life_time_value_of_customer` easily.

`SELECT litv_of_cst AS life_time_value_of_customer ...`

For all other easy-etl functionallity this column will now be considered `life_time_value_of_customer`.

## Transforming Data

The `transform` function accepts any field returned by the extract sql query
and allows the user to call any built-in python fucntion on that columns datatype.
Tranforms methods are exectued int he order they are added.

### Transforming with python built-ins

Upon the execution of the following process the strings of the `first_name` and `last_name` 
columns from the sql query will be converted to uppercase and have all spaces replaced with hyphens.
Any python builtin for that datatype can be used with the transform

`process.transform("first_name", "last_name").upper().replace(" ", "-")`

### Setting default values to replace nulls

According to Kimball null values in ETL processes should be replaced with human readable values so reports are easier to understand.
A simple `default` method has been included with the transform functionality of easy-etl to help facilitate this.

A table with two columns `smoker` and `sex` could be answered with one of two answers or left blank (null).  In the instance of a blank or null
we want to have the value `"unknown"` instead of null to make reading reports easier.

`process.transform("smoker", "sex").default("unknown")`

### Using custom transform functions

Sometimes builtins are not enough. Luckily, it is simple enough to use an external transform function.
**Your function needs to accept a value and return a value**

```python
def pig_latin(value):
    return "{}{}ay".format(value[1:] + value[0])

process.transform('col1', 'col2', 'col3').func(pig_latin)
```

### Linking related tables

For fact tables you will want to have foreign key references to your dimension tables.
Easy-etl makes this easy. All linking is executed after any transforms are executed. 

```python
# Will add a "column_name" field to the target_db of the table where the
# value of the id of the row in "child_table" where "child_field" matches
# the "parent_field" of the row being currently loaded.

# The name kwarg is optional.
process.link("parent_field", "child_table", "child_field", name="column_name")
```

**Note that you cannot use transform functionality on links**

### Linking related tables via closes value

Sometimes the link cannot be exact.  This is usually the case when dealing with a date dimension.
Our date dimension may have rows with July 1st and July 2nd at 00:00:00.
The table we are creating may have an entry that was placed at July 1st 12:45:38 and we want to
link it to the July 1st row of our date dimension.  This can be done easily as well.

```python
# >= is the default method.
process.link_closest("parent_field", "target_field", "child_table", "child_field",
                     name="column_name", method=">=")
```

Parent field is the value in the fact table that correlates with the child_table's child_field.
Target field is the field we want to compare when linking.

## Loading Data

Upon the `load` call the data is extracted and trasformed the loaded into the specified table
in the target database.

All fields loaded with easy-etl automatically receive an auto-incremented surrogate primary key.

### Inserting data

By default `load` will insert all extracted data as new entries.  This is perfect for periodic
snapshot fact tables. Use `ensure=True` kwarg if new columns are going to be added.

`process.load()`

### Upserting data

Sometime we don't want to insert new data with every load.  Sometimes we want to update or insert
tables into a table.   Say we have a client dimension where we want to update any client
that has recently changed the location data but we also want to add any new clients to our table.
That is also easy.  We just pass the fields we want to match for updates as a list to the
`upsert_fields` kwarg of the load function.  Use `ensure=True` kwarg if new columns are going to be added.

`process.load(upsert_fields=["client_id"], ensure=True)`

### Dropping unused columns

If your ETL process changes and doesn't include specific columns easy-etl will
automatically drop those columns from the table the next time the process is run.
You can disable this functionality via the `load` function's `safe` kwarg.

`process.load(safe=True)`

**Sqlite does not support dropping columns**

### Ignoring specific fields

Usually when linking related tables the field used to link the tables is not needed in the final
table schema.  These fields can be ignored when loading the data into the target database.

`process.ignore("field1", "field2")`


# Developers

## Running the tests

1. `pip install -r reqs.txt`
2. `vagrant up`
3. `tox`
