#!/bin/zsh

if [ -z "$1" ]; then
    echo "Usage: ./tagged_to_map.sh [filename_in_interim]"
    exit 1
fi

FILE_NAME=$1
BASE_NAME="${FILE_NAME%.*}"
SCRIPT_DIR="scripts"
DATA_DIR="data/interim"

INPUT_PATH="$DATA_DIR/$FILE_NAME"
OUTPUT_A="$DATA_DIR/${BASE_NAME}_cleaned.csv"
OUTPUT_B="$DATA_DIR/${BASE_NAME}_cleaned_mesh.csv"

set -e

echo "--- Start ---"

uv run "$SCRIPT_DIR/remove_noise.py" --input "$INPUT_PATH"
uv run "$SCRIPT_DIR/assign_mesh.py" --input "$OUTPUT_A"
uv run "$SCRIPT_DIR/mapping_tweets.py" --input "$OUTPUT_B" --simple

echo "--- Done! ---"
