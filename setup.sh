#!/bin/bash

# Pull the submodule 'immunefi-terminal'
git submodule update --init --recursive immunefi-terminal

# Navigate to the submodule 'immunefi-terminal'
cd immunefi-terminal

# Pull the submodule 'targets'
git submodule update --init --recursive targets

# Navigate back to the main directory
cd ..

# Set up virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install requirements for 'immunefi-terminal'
pip install -r immunefi-terminal/requirements.txt

# Install requirements for 'core'
pip install -r requirements.txt
