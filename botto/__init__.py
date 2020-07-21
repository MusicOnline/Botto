import yaml

# Read config.yaml first as the other imports rely on it

try:
    with open("config.yml") as file:
        config = yaml.full_load(file)  # pylint: disable=invalid-name
except FileNotFoundError as exc:
    raise FileNotFoundError(
        "The bot requires a config.yml file with the necessary values to start. "
        "Please read the original README.md file which can be found on "
        "https://github.com/MusicOnline/Botto for more information."
    ) from exc

# pylint: disable=wrong-import-position

from . import utils
from .core import *
from .utils.constants import *
