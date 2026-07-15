# artist_logs/fields.py
from django.db import models
import json

class ListField(models.TextField):
    """
    A custom field that stores a Python list as a JSON string.
    Works with any database backend (PostgreSQL, SQLite, MySQL, etc.).
    """
    description = "Stores a Python list as JSON"

    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return []

    def to_python(self, value):
        if isinstance(value, list):
            return value
        if value is None:
            return value
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return []

    def get_prep_value(self, value):
        if value is None:
            return value
        return json.dumps(value)

    def value_to_string(self, obj):
        value = self.value_from_object(obj)
        return self.get_prep_value(value)