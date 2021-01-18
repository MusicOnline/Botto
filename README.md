# Botto

![Python][python-shield]
[![discord.py][discordpy-shield]][discordpy-url]
[![License][license-shield]][license-url]
[![Issues][issues-shield]][issues-url]
[![Commits][commits-shield]][commits-url]
[![Discord][discord-shield]][discord-url]

[python-shield]: https://img.shields.io/badge/python-3.7%20%7C%203.8-blue.svg
[discordpy-shield]: https://img.shields.io/badge/discord.py-1.6.0-g
[discordpy-url]: https://github.com/Rapptz/discord.py/tree/v1.6.0
[license-shield]: https://img.shields.io/github/license/MusicOnline/Botto
[license-url]: https://github.com/MusicOnline/Botto/blob/master/LICENSE
[issues-shield]: https://img.shields.io/github/issues/MusicOnline/Botto
[issues-url]: https://github.com/MusicOnline/Botto/issues
[commits-shield]: https://img.shields.io/github/commit-activity/m/MusicOnline/Botto
[commits-url]: https://github.com/MusicOnline/Botto/commits
[discord-shield]: https://img.shields.io/discord/470114854762577920?color=%237289DA&label=chat%2Fsupport&logo=discord&logoColor=white
[discord-url]: https://discord.gg/wp7Wxzs

A template for bots written using discord.py.
As much I'd like to release this on PyPI, it seems more logical for this git repository to be forked and worked off of.
This project is very much still work in progress.

You may read the documentation for discord.py [here](https://discordpy.readthedocs.io/en/latest/index.html).
You can join the Discord server for support using this template.

## Installation and usage

### Requirements

-   Python 3.7 and above

### Installation

1. Fork this repository.

2. Run this command in your command line:

    ```bash
    git clone https://github.com/{YOUR_USERNAME}/Botto.git
    cd Botto
    pip install pipenv
    pipenv install  # prepend "python3 -m" as necessary
    ```

    If your machine does not have git, you may download it [here](https://git-scm.com/download/win).

3. Start hacking.

### Usage

1. Copy `config-example.yml` to `config.yml` in the same directory.
2. Fill up all necessary configuration values.
3. Run this command in your command line:
    ```bash
    pipenv run python -m botto  # prepend "python3 -m" as necessary
    ```
    Your bot should be online now.

## Gateway intents

Discord now has [Gateway Intents][gateway-intents-docs] which help (or force) you to limit events received. Privileged intents require verification for bots in over 100 guilds. No intents are necessary to function but `*_MESSAGES` intents should be enabled to receive messages.

| Configuration name | Actual intent name             |
| ------------------ | ------------------------------ |
| `GUILDS`           | _same_                         |
| `MEMBERS`          | `GUILD_MEMBERS` (Privileged)   |
| `BANS`             | `GUILD_BANS`                   |
| `EMOJIS`           | `GUILD_EMOJIS`                 |
| `INTEGRATIONS`     | `GUILD_INTEGRATIONS`           |
| `WEBHOOKS`         | `GUILD_WEBHOOKS`               |
| `INVITES`          | `GUILD_INVITES`                |
| `VOICE_STATES`     | `GUILD_VOICE_STATES`           |
| `PRESENCES`        | `GUILD_PRESENCES` (Privileged) |
| `GUILD_MESSAGES`   | _same_                         |
| `GUILD_REACTIONS`  | `GUILD_MESSAGE_REACTIONS`      |
| `GUILD_TYPING`     | `GUILD_MESSAGE_TYPING`         |
| `DM_MESSAGES`      | `DIRECT_MESSAGES`              |
| `DM_REACTIONS`     | `DIRECT_MESSAGE_REACTIONS`     |
| `DM_TYPING`        | `DIRECT_MESSAGE_TYPING`        |

[gateway-intents-docs]: https://discord.com/developers/docs/topics/gateway#gateway-intents

### `GUILDS` intent

If enabled, statistics embeds from `on_ready` events and the `botstats` command will show the number of guilds, text channels and voice channels the bot is in.

### `MEMBERS` privileged intent

If enabled, statistics embeds from `on_ready` events and the `botstats` command will show the number of guild members and unique users the bot can see. If the `PRESENCES` privileged intent is disabled, they will also show the number of bots it can see.

### `PRESENCES` privileged intent

If enabled together with the `MEMBERS` privileged intent, statistics embeds from `on_ready` events and the `botstats` command will show the number of guild members, unique users and online users the bot can see.

### `GUILD_MESSAGES` and `DM_MESSAGES` intents

If enabled, the bot can read sent messages and therefore execute commands in guild text channels and DM channels respectively.

### `GUILD_REACTIONS` and `DM_REACTIONS` intents

If enabled, the bot will send a 🗑️ `:wastebasket:` reaction when the `shell` and `eval` commands create a gist. It will listen to it for gist deletion.

## Contributing

Contributions are always welcome. You may also open issues on the issue tracker.<br>
Please see [CONTRIBUTING.md](./CONTRIBUTING.md) for further details.
