#!/usr/bin/env bash
# Record Agent2048 visual demo with asciinema
# Output: demo.cast (can be uploaded to asciinema.org or shared)

set -e

CAST_FILE="${1:-demo.cast}"

echo "Recording Agent2048 visual demo to $CAST_FILE..."
echo "Press Ctrl+D or type 'exit' when done"
echo ""

# Run the visual demo inside asciinema
asciinema rec "$CAST_FILE" --command="python /home/liskil/hackaton/examples/visual_demo.py" --idle-time-limit=1

echo ""
echo "✓ Recording saved to $CAST_FILE"
echo ""
echo "To share online:"
echo "  asciinema upload $CAST_FILE"
echo ""
echo "To view:"
echo "  asciinema play $CAST_FILE"
