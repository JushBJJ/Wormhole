#!/bin/bash

CONFIG_FILES=("config.json" ".env")
CONFIG_DIRS=("tox")
DISCORD_SCRIPT="run_discord.py"
BUILD_DIR="build"
BACKUP_DIR="backup"

preserve_files() {
    mkdir -p "$BACKUP_DIR"
    for file in "${CONFIG_FILES[@]}"; do
        cp "$file" "$BACKUP_DIR/$file.bak"
    done
    for dir in "${CONFIG_DIRS[@]}"; do
        cp -r "$dir" "$BACKUP_DIR/$dir.bak"
    done
    echo "Your files have been backed up in the $BACKUP_DIR directory."
}

restore_files() {
    for file in "${CONFIG_FILES[@]}"; do
        cp "$BACKUP_DIR/$file.bak" "$file"
    done
    for dir in "${CONFIG_DIRS[@]}"; do
        rm -rf "$dir"
        cp "$BACKUP_DIR/$dir.bak" "$dir"
    done
}

check_for_updates() {
    git fetch
    local status_output
    status_output=$(git status -uno)
    if [[ "$status_output" == *"Your branch is behind"* ]]; then
        return 0
    else
        return 1
    fi
}

pull_updates() {
    preserve_files
    if git pull; then
        notify_user "Updates have been successfully pulled."
        restore_files
    else
        notify_user "Failed to pull updates. Restoring the original files."
        restore_files
        exit 1
    fi
}

notify_user() {
    local message=$1
    echo "[Wormhole] $message"
}

prompt_user() {
    read -p "Updates are available. Do you want to pull the latest changes? (Y/N): " choice
    case "$choice" in
        [Yy]* ) return 0 ;;
        [Nn]* ) return 1 ;;
        * ) echo "Please answer Y or N." ;;
    esac
}

main() {
    if check_for_updates; then
        if prompt_user; then
            notify_user "Pulling the latest changes..."
            pull_updates
        else
            notify_user "Skipping updates."
        fi
    else
        notify_user "No updates are available."
    fi

    notify_user "Cleaning and rebuilding the project..."
    rm -rf "$BUILD_DIR"
    mkdir "$BUILD_DIR"
    cd "$BUILD_DIR" || exit
    cmake ..
    make
    cd ..

    notify_user "Setting up the Python environment..."
    source .venv/bin/activate
    pip install -r requirements.txt

    echo "############################################"
    echo "Please run the following commands in separate terminals:"
    echo "1. To start the Discord bot: python $DISCORD_SCRIPT"
    echo "2. To start the Tox node: ./Wormhole_Node"
    echo "############################################"
}

main
