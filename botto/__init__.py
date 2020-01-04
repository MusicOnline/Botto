import yaml

# Read config.yaml first as the other imports rely on it

try:
    with open("config.yaml") as file:
        config = yaml.full_load(file)
except FileNotFoundError as e:
    raise FileNotFoundError(
        "The bot requires a config.yaml file with the necessary values to start. "
        "Please read the original README.md file which can be found on "
        "https://github.com/MusicOnline/Botto for more information."
    ) from e

from . import utils
from .core import *
from .utils.constants import *
