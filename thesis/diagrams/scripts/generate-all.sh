#!/bin/bash
# generate-all.sh - Generate HTML, SVG, and PNG outputs for all diagrams

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR/source"
OUTPUT_DIR="$SCRIPT_DIR/output"

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== PaaS Diagram Generator ===${NC}"
echo "Source: $SOURCE_DIR"
echo "Output: $OUTPUT_DIR"
echo ""

# Create output directories
mkdir -p "$OUTPUT_DIR/html"
mkdir -p "$OUTPUT_DIR/svg"
mkdir -p "$OUTPUT_DIR/png"

# Find all compact markdown files
DIAGRAMS=$(find "$SOURCE_DIR" -name "*_compact.md" | sort)

if [ -z "$DIAGRAMS" ]; then
    echo -e "${YELLOW}No *_compact.md files found in $SOURCE_DIR${NC}"
    exit 1
fi

echo -e "${GREEN}Found $(echo "$DIAGRAMS" | wc -l) diagrams to process${NC}"
echo ""

# Process each diagram
for MD_FILE in $DIAGRAMS; do
    BASENAME=$(basename "$MD_FILE" .md)
    TITLE=$(head -n 1 "$MD_FILE" | sed 's/^# //')

    echo -e "${BLUE}Processing: ${BASENAME}${NC}"

    # Extract mermaid code block
    MERMAID_CODE=$(sed -n '/```mermaid/,/```/p' "$MD_FILE" | sed '1d;$d')

    if [ -z "$MERMAID_CODE" ]; then
        echo -e "${YELLOW}  ⚠ No mermaid code found, skipping${NC}"
        continue
    fi

    # Generate HTML with versioning
    HTML_FILE="$OUTPUT_DIR/html/${BASENAME}.html"

    # Check if file exists and add version number
    if [ -f "$HTML_FILE" ]; then
        VERSION=1
        while [ -f "$OUTPUT_DIR/html/${BASENAME}_v${VERSION}.html" ]; do
            VERSION=$((VERSION + 1))
        done
        HTML_FILE="$OUTPUT_DIR/html/${BASENAME}_v${VERSION}.html"
        BASENAME="${BASENAME}_v${VERSION}"
    fi

    cat > "$HTML_FILE" <<EOF
<!DOCTYPE html>
<html lang="hu">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${TITLE}</title>
    <script type="module">
        import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
        mermaid.initialize({
            startOnLoad: true,
            theme: 'base',
            themeVariables: {
                primaryColor: '#e1f5fe',
                edgeLabelBackground: '#ffffff',
                tertiaryColor: '#f1f8e9',
                lineColor: '#333333',
                fontFamily: 'Arial, sans-serif',
                fontSize: '14px'
            },
            flowchart: {
                htmlLabels: true,
                curve: 'basis',
                padding: 15
            }
        });
    </script>
    <style>
        @page {
            size: A4;
            margin: 2cm;
        }

        body {
            font-family: 'Arial', sans-serif;
            background-color: #ffffff;
            margin: 0;
            padding: 20px;
            max-width: 210mm;
            margin: 0 auto;
        }

        .container {
            background: white;
            padding: 20px;
            border-radius: 8px;
        }

        h1 {
            color: #2c3e50;
            border-bottom: 3px solid #3498db;
            padding-bottom: 10px;
            margin-top: 0;
            font-size: 24px;
        }

        .diagram-container {
            display: flex;
            justify-content: center;
            margin: 20px 0;
            page-break-inside: avoid;
        }

        .mermaid {
            max-width: 100%;
        }

        .footer {
            margin-top: 30px;
            padding-top: 10px;
            border-top: 1px solid #eee;
            font-size: 12px;
            color: #666;
            text-align: center;
        }

        @media print {
            body {
                background: white;
                padding: 0;
            }
            .no-print {
                display: none;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>${TITLE}</h1>

        <div class="diagram-container">
            <div class="mermaid">
${MERMAID_CODE}
            </div>
        </div>

        <div class="footer">
            <p>PaaS Infrastructure Automation Framework | BME-VIK Diplomaterv</p>
        </div>
    </div>
</body>
</html>
EOF

    echo -e "  ${GREEN}✓${NC} HTML generated: html/${BASENAME}.html"
done

echo ""
echo -e "${GREEN}=== HTML Generation Complete ===${NC}"
echo -e "Generated files in: ${BLUE}${OUTPUT_DIR}/html/${NC}"
echo ""
echo "To generate SVG and PNG:"
echo "  1. Install mmdc: npm install -g @mermaid-js/mermaid-cli"
echo "  2. Run: ./generate-svg-png.sh"
echo ""
echo "Or use Docker:"
echo "  docker run --rm -v \"\$(pwd):/data\" minlag/mermaid-cli -i /data/source/phase1_user_onboarding_compact.md -o /data/output/svg/phase1.svg"
