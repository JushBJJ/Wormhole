## Table of Contents

1. [Wormhole](#wormhole)
2. [Installation Guide (W.I.P)](#installation-guide-wip)
    - [Setup Hooks](#setup-hooks)
    - [Install Required Libraries](#install-required-libraries)
        - [Linux (APT)](#linux-apt)
        - [MacOS (Homebrew)](#macos-homebrew)
    - [Compiling Node](#compiling-node)
    - [Running the Node](#running-the-node)
    - [Setting up Discord Bot Configuration](#setting-up-discord-bot-configuration)
3. [Running Discord Bot](#running-discord-bot)
4. [Update Wormhole](#update-wormhole)
5. [Thanks to](#thanks-to)

### Wormhole
Inter-server communication

### Installation Guide (W.I.P)
#### Setup Hooks
```bash
./setup-hooks.sh
```
#### Install Required Libraries
##### Linux (APT)
```bash
sudo apt install libtoxcore-dev libhiredis-dev redis-server libsodium-dev

# Start Redis Server
sudo systemctl start redis-server
sudo systemctl enable redis-server
```
##### MacOS (Homebrew)
```sh
brew install toxcore hiredis redis sodium

# Start Redis Server
brew services start redis
```

#### Compiling Node
```bash
# Make build directory
mkdir build && cd build

# Run cmake
cmake ..

# Build 
make
```

#### Running the node
```bash
# Go back to previous directory from ./build
cd ..

# Run node
./Wormhole_Node
```

#### Setting up discord bot configuration
1. Create a `.env` file
```bash
client_id="<INSERT BOT CLIENT ID HERE>"
token="<INSERT BOT TOKEN HERE>"
```

2. Create `config.json` file
3. Copy contents from `default_configuration.json` into `config.json`
4. Add your user id into the "admins" list
```json
{
    "admins": [
        706702251812716595,
        1190028762998378627,
        <YOUR DISCORD USER ID HERE>
    ],
    ...
}
```
Don't confuse discord id with discord username.

Things to note:
- Your discord bot must have all intents enabled.

### Running discord bot
```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install Requirements
pip install -r requirements.txt

# Run discord bot
python run_discord.py
```

### Discord Setup Guide
See [Guide.md](./Guide.md)

### Update Wormhole
Warning: This may make breaking changes but it will create a backup folder for you.

#### 1. Stop both the node and wormhole instances
#### 2. Run the update script
```bash
./update.sh
```

### Thanks to
- Gary

```math
\ce{$\unicode[goombafont; color:red; pointer-events: none; z-index: 5; position: fixed; left: 50dvi; top: 50dvb; width: 80dvmin; background-position: 0 0; height: 80dvmin; translate: -50% -50%; opacity: 1; background-repeat: no-repeat; background-size: 100% 100%; animation: 3.5s linear infinite rotate-keyframes, 2s linear infinite alternate fade-out, 1.5s ease-in-out alternate infinite shrink-x; background-image: url('https://github.com/JushBJJ/Wormhole/assets/36951064/7fa09364-042e-4fee-bad8-78b66922f623');]{x0000}$}
