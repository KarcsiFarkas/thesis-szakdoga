#!/bin/bash
# generate-svg-png-docker.sh - Generate SVG/PNG using Docker (no npm install needed)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR/source"
OUTPUT_DIR="$SCRIPT_DIR/output"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=== SVG/PNG Generator (Docker Method) ===${NC}"
echo ""

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo -e "${RED}ERROR: Docker not found${NC}"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

echo -e "${GREEN}Found Docker: $(docker --version)${NC}"
echo ""

# Create output directories
mkdir -p "$OUTPUT_DIR/svg"
mkdir -p "$OUTPUT_DIR/png"

# Find all compact markdown files
DIAGRAMS=$(find "$SOURCE_DIR" -name "*_compact.md" | sort)

if [ -z "$DIAGRAMS" ]; then
    echo -e "${YELLOW}No *_compact.md files found${NC}"
    exit 1
fi

TOTAL=$(echo "$DIAGRAMS" | wc -l)
CURRENT=0

echo -e "${GREEN}Found $TOTAL diagrams to process${NC}"
echo ""

# Pull Docker image if not exists
if ! docker image inspect minlag/mermaid-cli >/dev/null 2>&1; then
    echo -e "${BLUE}Pulling mermaid-cli Docker image...${NC}"
    docker pull minlag/mermaid-cli
    echo ""
fi

for MD_FILE in $DIAGRAMS; do
    CURRENT=$((CURRENT + 1))
    BASENAME=$(basename "$MD_FILE" .md)

    echo -e "${BLUE}[$CURRENT/$TOTAL] Processing: ${BASENAME}${NC}"

    # Generate SVG with versioning
    SVG_FILE="$OUTPUT_DIR/svg/${BASENAME}.svg"
    SVG_OUTPUT="${BASENAME}.svg"

    # Check if SVG exists and add version number
    if [ -f "$SVG_FILE" ]; then
        VERSION=1
        while [ -f "$OUTPUT_DIR/svg/${BASENAME}_v${VERSION}.svg" ]; do
            VERSION=$((VERSION + 1))
        done
        SVG_FILE="$OUTPUT_DIR/svg/${BASENAME}_v${VERSION}.svg"
        SVG_OUTPUT="${BASENAME}_v${VERSION}.svg"
    fi

    if docker run --rm -v "$SCRIPT_DIR:/data" minlag/mermaid-cli \
        -i "/data/source/${BASENAME}.md" \
        -o "/data/output/svg/${SVG_OUTPUT}" \
        -b transparent \
        -w 1200 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} SVG: svg/${SVG_OUTPUT}"
    else
        echo -e "  ${YELLOW}⚠${NC} SVG generation had warnings (might still work)"
    fi

    # Generate PNG with versioning
    PNG_FILE="$OUTPUT_DIR/png/${BASENAME}.png"
    PNG_OUTPUT="${BASENAME}.png"

    # Check if PNG exists and add version number
    if [ -f "$PNG_FILE" ]; then
        VERSION=1
        while [ -f "$OUTPUT_DIR/png/${BASENAME}_v${VERSION}.png" ]; do
            VERSION=$((VERSION + 1))
        done
        PNG_FILE="$OUTPUT_DIR/png/${BASENAME}_v${VERSION}.png"
        PNG_OUTPUT="${BASENAME}_v${VERSION}.png"
    fi

    if docker run --rm -v "$SCRIPT_DIR:/data" minlag/mermaid-cli \
        -i "/data/source/${BASENAME}.md" \
        -o "/data/output/png/${PNG_OUTPUT}" \
        -b white \
        -w 1200 \
        -s 2 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} PNG: png/${BASENAME}.png"
    else
        echo -e "  ${YELLOW}⚠${NC} PNG generation had warnings (might still work)"
    fi

    echo ""
done

echo -e "${GREEN}=== Generation Complete ===${NC}"
echo ""
echo "Output locations:"
echo -e "  SVG: ${BLUE}${OUTPUT_DIR}/svg/${NC}"
echo -e "  PNG: ${BLUE}${OUTPUT_DIR}/png/${NC}"
echo ""
echo "Next step: Run ./generate-all.sh to create index.html"
