import logging
import sys

from botto import Botto

# Logging
dpy_logger: logging.Logger = logging.getLogger("discord")
dpy_logger.setLevel(logging.WARNING)
logger: logging.Logger = logging.getLogger("botto")
logger.setLevel(logging.INFO)

formatter: logging.Formatter = logging.Formatter(
    "[{asctime}] [{levelname:>8}] {name}: {message}", style="{"
)

stream_handler: logging.StreamHandler = logging.StreamHandler(sys.stdout)
file_handler: logging.FileHandler = logging.FileHandler(
    filename="botto.log", encoding="utf-8", mode="w"
)
error_file_handler: logging.FileHandler = logging.FileHandler(
    filename="error.log", encoding="utf-8", mode="w"
)

stream_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)
error_file_handler.setFormatter(formatter)
error_file_handler.setLevel(logging.ERROR)

dpy_logger.addHandler(stream_handler)
dpy_logger.addHandler(file_handler)
dpy_logger.addHandler(error_file_handler)
logger.addHandler(stream_handler)
logger.addHandler(file_handler)
logger.addHandler(error_file_handler)

# Bot
bot: Botto = Botto()

bot.run()
