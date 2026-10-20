from django.db import models
from django.db.models.expressions import UUID
from django.db.models.functions.text import CharField
import uuid # i don't know that if this uuid is THAT uuid

# Create your models here.

class Book(models.Model):
    id = models.UUIDField(
        primary_key = True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    borrowed = models.BooleanField()

    def __str__(self):
        return f"{self.name} - {self.author}"
