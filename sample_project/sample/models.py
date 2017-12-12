from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.db import models
from magi.item_model import MagiModel
from magi.abstract_models import BaseAccount

# Create your models here.

class Account(BaseAccount):
    class Meta:
        pass
