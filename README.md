# Wormhole
Inter-server communication bot

## Supports
- Discord
- Telegram
- Signal

# TODO
- Optimize speed
- "Decentralised" discord servers

## Libraries needed
- libtoxcore-dev
- libhiredis-dev
- redis-server
- libsodium-dev

## Installation Guide (W.I.P)
### Install Required Libraries
#### Linux (APT)
```bash
sudo apt install libtoxcore-dev libhiredis-dev redis-server libsodium-dev
```
#### MacOS (Homebrew)
```sh
brew install toxcore hiredis redis sodium
```

### Compiling Node
```bash
# Make build directory
mkdir build && cd build

# Run cmake
cmake ..

# Build 
make
```

### Running the node
```
# Go back to previous directory from ./build
cd ..

# Run node
./Wormhole_Node
```

### Setting up discord bot configuration
1. Create a `.env` file
```
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

### Running discord bot
```bash
# Create virtual environent
python -m venv .venv
source .venv/bin/activate

# Install Requirements
pip install -r requirements.txt

# Run discord bot
python run_discord.py
```

More coming soon...

## Thanks to
- Gary