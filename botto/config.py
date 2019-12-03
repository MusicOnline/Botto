import os

BOT_TOKEN = os.getenv("BOTTO_TOKEN")
DATABASE_URI = os.getenv("DB")

OWNER_ID = 0  # int
CONSOLE_CHANNEL_ID = None # Optional[int]

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

MAIN_COLOUR = 0xFFFFFF  # int or discord.Colour
PREFIXES = ["botto "]  # List[str]
