#!/bin/bash

cp scripts/hooks/* .git/hooks/
chmod +x .git/hooks/*

echo "Hooks now set up"
