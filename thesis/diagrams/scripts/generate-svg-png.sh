#!/bin/bash
# generate-svg-png.sh - Generate SVG and PNG from markdown diagrams using mermaid-cli

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

echo -e "${BLUE}=== SVG/PNG Generator (using mermaid-cli) ===${NC}"
echo ""

# Check if mmdc is installed
if ! command -v mmdc &> /dev/null; then
    echo -e "${RED}ERROR: mmdc (mermaid-cli) not found${NC}"
    echo ""
    echo "Install options:"
    echo "  1. npm install -g @mermaid-js/mermaid-cli"
    echo "  2. Use Docker method (see generate-svg-png-docker.sh)"
    echo ""
    exit 1
fi

echo -e "${GREEN}Found mmdc: $(which mmdc)${NC}"
echo ""

# Create output directories
mkdir -p "$OUTPUT_DIR/svg"
mkdir -p "$OUTPUT_DIR/png"

# Configuration file for mermaid-cli
MMDC_CONFIG="$OUTPUT_DIR/puppeteer-config.json"
cat > "$MMDC_CONFIG" <<EOF
{
  "theme": "base",
  "themeVariables": {
    "primaryColor": "#e1f5fe",
    "edgeLabelBackground": "#ffffff",
    "tertiaryColor": "#f1f8e9",
    "lineColor": "#333333",
    "fontFamily": "Arial",
    "fontSize": "14px"
  },
  "flowchart": {
    "htmlLabels": true,
    "curve": "basis",
    "padding": 15
  }
}
EOF

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

for MD_FILE in $DIAGRAMS; do
    CURRENT=$((CURRENT + 1))
    BASENAME=$(basename "$MD_FILE" .md)

    echo -e "${BLUE}[$CURRENT/$TOTAL] Processing: ${BASENAME}${NC}"

    # Generate SVG with versioning
    SVG_FILE="$OUTPUT_DIR/svg/${BASENAME}.svg"

    # Check if SVG exists and add version number
    if [ -f "$SVG_FILE" ]; then
        VERSION=1
        while [ -f "$OUTPUT_DIR/svg/${BASENAME}_v${VERSION}.svg" ]; do
            VERSION=$((VERSION + 1))
        done
        SVG_FILE="$OUTPUT_DIR/svg/${BASENAME}_v${VERSION}.svg"
        SVG_OUTPUT="${BASENAME}_v${VERSION}.svg"
    else
        SVG_OUTPUT="${BASENAME}.svg"
    fi

    if mmdc -i "$MD_FILE" -o "$SVG_FILE" -c "$MMDC_CONFIG" -b transparent -w 1200 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} SVG: svg/${SVG_OUTPUT}"
    else
        echo -e "  ${RED}✗${NC} SVG generation failed"
    fi

    # Generate PNG (A4 width: 210mm = ~794px at 96dpi, use 1200px for quality) with versioning
    PNG_FILE="$OUTPUT_DIR/png/${BASENAME}.png"

    # Check if PNG exists and add version number
    if [ -f "$PNG_FILE" ]; then
        VERSION=1
        while [ -f "$OUTPUT_DIR/png/${BASENAME}_v${VERSION}.png" ]; do
            VERSION=$((VERSION + 1))
        done
        PNG_FILE="$OUTPUT_DIR/png/${BASENAME}_v${VERSION}.png"
        PNG_OUTPUT="${BASENAME}_v${VERSION}.png"
    else
        PNG_OUTPUT="${BASENAME}.png"
    fi

    if mmdc -i "$MD_FILE" -o "$PNG_FILE" -c "$MMDC_CONFIG" -b white -w 1200 -s 2 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} PNG: png/${PNG_OUTPUT}"
    else
        echo -e "  ${RED}✗${NC} PNG generation failed"
    fi

    echo ""
done

# Cleanup
rm -f "$MMDC_CONFIG"

echo -e "${GREEN}=== Generation Complete ===${NC}"
echo ""
echo "Output locations:"
echo -e "  SVG: ${BLUE}${OUTPUT_DIR}/svg/${NC}"
echo -e "  PNG: ${BLUE}${OUTPUT_DIR}/png/${NC}"
echo ""

# Generate index
echo -e "${BLUE}Generating index.html...${NC}"

INDEX_FILE="$OUTPUT_DIR/index.html"
cat > "$INDEX_FILE" <<'EOF'
<!DOCTYPE html>
<html lang="hu">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PaaS Diagram Index</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
        }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 30px;
        }
        .card {
            background: white;
            border-radius: 8px;
            padding: 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        .card:hover {
            transform: translateY(-5px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
        .card h2 {
            color: #3498db;
            margin-top: 0;
            font-size: 18px;
        }
        .links {
            display: flex;
            gap: 10px;
            margin-top: 15px;
        }
        .links a {
            display: inline-block;
            padding: 8px 15px;
            background: #3498db;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            font-size: 14px;
        }
        .links a:hover {
            background: #2980b9;
        }
        .badge {
            display: inline-block;
            padding: 4px 8px;
            background: #e74c3c;
            color: white;
            border-radius: 3px;
            font-size: 12px;
            margin-left: 10px;
        }
    </style>
</head>
<body>
    <h1>PaaS Infrastructure Automation - Diagram Index</h1>
    <p>BME-VIK Diplomaterv | Platform-as-a-Service Automatizálási Keretrendszer</p>

    <div class="grid">
EOF

# Add cards for each diagram
find "$OUTPUT_DIR/html" -name "*.html" ! -name "index.html" | sort | while read HTML_FILE; do
    BASENAME=$(basename "$HTML_FILE" .html)
    TITLE=$(grep -m 1 "<title>" "$HTML_FILE" | sed 's/.*<title>\(.*\)<\/title>.*/\1/')

    # Extract phase number if exists
    PHASE=$(echo "$BASENAME" | grep -oP 'phase\d+[ab]?' || echo "summary")

    cat >> "$INDEX_FILE" <<CARD
        <div class="card">
            <h2>$TITLE <span class="badge">$PHASE</span></h2>
            <div class="links">
                <a href="html/$BASENAME.html" target="_blank">HTML</a>
                <a href="svg/$BASENAME.svg" target="_blank">SVG</a>
                <a href="png/$BASENAME.png" target="_blank">PNG</a>
            </div>
        </div>
CARD
done

cat >> "$INDEX_FILE" <<'EOF'
    </div>

    <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #666;">
        <p>Generated on: <script>document.write(new Date().toLocaleString('hu-HU'))</script></p>
    </div>
</body>
</html>
EOF

echo -e "${GREEN}✓${NC} Index generated: index.html"
echo ""
echo -e "Open ${BLUE}${OUTPUT_DIR}/index.html${NC} in your browser to view all diagrams"
