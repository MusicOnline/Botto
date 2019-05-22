import logging
import sys

from . import config
from .core import Botto

# Logging
dpy_logger: logging.Logger = logging.getLogger("discord")
dpy_logger.setLevel(logging.WARNING)
logger: logging.Logger = logging.getLogger("botto")
logger.setLevel(logging.INFO)

formatter: logging.Formatter = logging.Formatter(
    "[{asctime}] [{levelname:>8}] {name}: {message}", style="{"
)

stream_hdlr: logging.StreamHandler = logging.StreamHandler(sys.stdout)
file_hdlr: logging.FileHandler = logging.FileHandler(
    filename="botto.log", encoding="utf-8", mode="w"
)

stream_hdlr.setFormatter(formatter)
file_hdlr.setFormatter(formatter)

dpy_logger.addHandler(stream_hdlr)
dpy_logger.addHandler(file_hdlr)
logger.addHandler(stream_hdlr)
logger.addHandler(file_hdlr)

# Bot
bot: Botto = Botto()

bot.load_extension("jishaku")
bot.load_extension("botto.modules.events")
bot.load_extension("botto.modules.owner")
bot.load_extension("botto.modules.meta")
bot.load_extension("botto.modules.help")

bot.run(config.BOT_TOKEN)
