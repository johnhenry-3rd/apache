# -*- coding: utf-8 -*-
from __future__ import absolute_import, division, print_function, unicode_literals

import json

import six

try:
    from django.contrib.postgres.aggregates import ArrayAgg, StringAgg
except ImportError:

    def NoPostgres(*args, **kwargs):
        raise NotImplementedError("Postgres not installed")

    ArrayAgg = StringAgg = NoPostgres
from django.db import models
from django.db.models import Avg, Count, Expression, Max, Min, Sum, Value
from django.db.models.functions import Cast, Concat
from tabulate import tabulate

__all__ = ["queryset_table", "instance_table"]


class FormatStringParseError(Exception):
    pass


def format_string_tokens(string_to_parse):
    text_field = models.TextField()

    def value(value):
        return Value(value, output_field=text_field)

    def field(name):
        return Cast(name, output_field=text_field)

    current = ""
    current_type = value
    for i, c in enumerate(string_to_parse):
        if c == "{":
            if current_type == field:
                raise FormatStringParseError("Can't nest fields ay char {}".format(i))
            if current:
                yield current_type(current)
            current = ""
            current_type = field
        elif c == "}":
            if current_type != field:
                raise FormatStringParseError(
                    "Can't end field that hasn't been started at char {}".format(i)
                )
            if current:
                yield current_type(current)
            current = ""
            current_type = value
        else:
            current += c
    if current:
        yield current_type(current)


def format_string(string):
    return Concat(*format_string_tokens(string))


def stringify(value):
    if isinstance(value, dict):
        return json.dumps(value, indent=2)
    return six.text_type(value)


aggregate_functions = {
    "[]": {"function": ArrayAgg, "name": "list"},
    "1[]": {"function": ArrayAgg, "name": "list", "kwargs": {"distinct": True}},
    "*": {"function": StringAgg, "name": "group", "kwargs": {"delimiter": ", "}},
    "1*": {
        "function": StringAgg,
        "name": "group",
        "kwargs": {"delimiter": ", ", "distinct": True},
    },
    "#": {"function": Count, "name": "count"},
    "1#": {"function": Count, "name": "count", "kwargs": {"distinct": True}},
    "^": {"function": Max, "name": "max"},
    "_": {"function": Min, "name": "max"},
    "+": {"function": Sum, "name": "sum"},
    "~": {"function": Avg, "name": "sum"},
}


def queryset_table(
    queryset,
    fields,
    table_format="fancy_grid",
    print_result=True,
    filter=None,
    slice=None,
    show_keys=False,
):
    groups = {}
    headers = []
    for index, field in enumerate(fields):
        key = field
        header = None
        if isinstance(field, tuple):
            field, header = field
            fields[index] = field
            key = field

        if isinstance(field, Expression):
            if not header:
                header = six.text_type(field)
            key = "field_{}".format(index)
            groups[key] = field
            fields[index] = key
        elif isinstance(field, six.string_types):
            if not header:
                header = field.replace("_", " ").replace("  ", " ").strip().title()
            if field.startswith("f|"):
                key = "field_{}".format(index)
                fields[index] = key
                groups[key] = format_string(field[2:])
            else:
                for prefix in aggregate_functions.keys():
                    if field.startswith(prefix):
                        field = field[len(prefix) :]
                        key = "_{}_{}".format(
                            aggregate_functions[prefix]["name"], field
                        )
                        fields[index] = key
                        func = aggregate_functions[prefix]
                        groups[key] = func["function"](field, **func.get("kwargs", {}))
        else:
            raise ValueError("Field must be a string or expression")
        if show_keys:
            header = "{} ({})".format(header, key)
        headers.append(header)
    if not filter:
        filter = {}
    records = queryset.annotate(**groups).filter(**filter).values(*fields)
    if slice:
        start, end = slice
        records = records[start:end]
    if table_format == "tsv":
        table = "\n".join(
            "\t".join(str(record[field]) for field in fields) for record in records
        )
    else:
        table = tabulate(
            ([stringify(record[field]) for field in fields] for record in records),
            headers=headers,
            tablefmt=table_format,
        )

    if print_result:
        print(table)
    else:
        return table


def instance_table(
    instance, private=False, table_format="fancy_grid", print_result=True
):
    table = tabulate(
        (
            (key, stringify(value))
            for key, value in sorted(six.iteritems(instance.__dict__))
            if private or not key.startswith("_")
        ),
        tablefmt=table_format,
    )
    if print_result:
        print(table)
    else:
        return table
