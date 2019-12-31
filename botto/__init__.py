import yaml

with open("config.yaml") as file:
    config = yaml.full_load(file)

from . import utils
from .core import *
from .utils.constants import *
