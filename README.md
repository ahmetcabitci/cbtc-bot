
# CBTC Bot

CBTC Bot is a music bot developed for playing music in TeamTalk channels. It plays local music files and songs found through YouTube searches. Each search returns up to 10 results. The bot plays the first result and allows users to move between tracks.

## Version Information

**Planned release:** v1.0.0

You can find published versions of CBTC Bot and their release notes on GitHub.

[View Latest Release](https://github.com/ahmetcabitci/cbtc-bot/releases/latest)

## Official Website

For detailed information about CBTC Bot, its features, and an introduction to the project, visit the official website:

[CBTC Bot – Official Website (Turkish)](https://www.ahmetcabitci.com.tr/cbtc-bot/)

## Installation

For a fresh installation on Ubuntu 24.04 and 26.04 x86_64, open the [KURULUM.txt](KURULUM.txt) file.

The installation guide provides step-by-step commands to run in PuTTY and explains what each command does.

The bot is downloaded directly from a GitHub ZIP archive without requiring Git.

The Ubuntu 24 SDK files are not included in the GitHub package. Obtain them separately from the developer as a ZIP archive and place them in the directory specified in the installation guide.

The `tools/sdk_indir.py` script verifies these files.

On Ubuntu 26.04, the same tool downloads the appropriate SDK package from BearWare's official website.

**Note:** Installation on Ubuntu 26.04 has not yet been verified on a live server.

## Usage

You can control the bot through private messages in TeamTalk.

- `o artist song` — Searches YouTube and plays the first result.
- `d` — Stops playback.
- `i` — Plays the next track.
- `g` — Plays the previous track.
- `y` — Displays the help menu.

Administrator settings and additional commands are also explained in the help menu.

The bot can run in the background as a systemd service.

The `yt-dlp` component used to retrieve YouTube audio checks for new stable releases on GitHub in the background.

## Developer and Contact

**Developer:** Ahmet Çabıtçı

**Email:** cabitciahmet@gmail.com

**Telegram group:** [CBTC Bot](https://t.me/cabitcibot)

## License

CBTC Bot is free and open-source software released under the GNU General Public License v3.0 (GPL-3.0).

You are free to use, study, modify, and redistribute the software in accordance with the license terms.

For the full license terms, see the [LICENSE](LICENSE) file.

## Contributing

Contributions to the development of CBTC Bot are welcome.

You can report bugs, suggest new features, and submit improvements through pull requests on GitHub.

Developers interested in contributing can visit the project repository:

[CBTC Bot GitHub Repository](https://github.com/ahmetcabitci/cbtc-bot)

## Languages

- English: README.md
- Turkish: [README.tr.md](README.tr.md)
