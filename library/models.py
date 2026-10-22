from cmd import PROMPT

from django.db import models
from django.db.models.expressions import UUID
from django.db.models.functions.text import CharField
import uuid # i don't know that if this uuid is THAT uuid
from django.conf import settings

# Create your models here.

class Book(models.Model):
    id = models.UUIDField(
        primary_key = True,
        default=uuid.uuid4,
        editable=False
    )
    name = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    # we use relations to user
    borrowed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null = True,
        blank = True,
        on_delete=models.SET_NULL,
        related_name = "borrowed_books"
    )

    # we use this one so we don't need the borrowed boolean field
    @property
    def borrowed(self):
        return self.borrowed_by is not None

    def __str__(self):
        return f"{self.name} - {self.author}"
