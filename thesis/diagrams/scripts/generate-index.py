#!/usr/bin/env python3
"""Generate index.html for all diagram outputs"""

import os
import argparse
from pathlib import Path

def parse_args():
    parser = argparse.ArgumentParser(description="Generate index.html for diagram outputs")
    parser.add_argument(
        "-o",
        "--output-dir",
        default="output",
        help="Base output directory containing the html subdirectory.",
    )
    return parser.parse_args()

def get_diagram_title(html_path, basename):
    try:
        with open(html_path, 'r', encoding='utf-8') as hf:
            for line in hf:
                if '<title>' in line:
                    return line.split('<title>')[1].split('</title>')[0]
    except Exception:
        pass
    return basename.replace('_', ' ').title()

def generate_card(html_path, basename):
    title = get_diagram_title(html_path, basename)
    
    if 'phase' in basename:
        phase_parts = basename.split('_')
        # Try to get phase number like "phase1"
        phase = phase_parts[0]
    elif 'summary' in basename:
        phase = "Summary"
    elif 'complete' in basename:
        phase = "Complete Flow"
    else:
        phase = "Misc"

    return f'''        <div class="card">
            <div class="card-header">
                <h2>{title}</h2>
                <span class="badge">{phase}</span>
            </div>
            <div class="links">
                <a href="html/{basename}.html" target="_blank">View Diagram</a>
            </div>
        </div>
'''

def main():
    args = parse_args()
    
    # Handle relative paths
    base_dir = Path.cwd()
    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = base_dir / output_dir

    html_dir = output_dir / "html"

    print("=== Generating Index ===\n")
    print(f"Scanning for HTML files in: {html_dir}")

    if not html_dir.exists():
         print(f"ERROR: Directory not found: {html_dir}")
         return

    # Find all HTML files except index.html
    html_files = sorted([f for f in html_dir.glob("*.html") if f.name != "index.html"])

    if not html_files:
        print("ERROR: No HTML files found")
        return

    # Split into categories
    sequence_diagrams = []
    infra_diagrams = []

    for f in html_files:
        if "_sequence" in f.name:
            sequence_diagrams.append(f)
        else:
            infra_diagrams.append(f)

    print(f"Found {len(infra_diagrams)} Infrastructure Diagrams")
    print(f"Found {len(sequence_diagrams)} Sequence Diagrams\n")

    # Generate index.html
    index_file = output_dir / "index.html"

    with open(index_file, 'w', encoding='utf-8') as f:
        f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PaaS Diagram Index</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 1600px;
            margin: 0 auto;
            padding: 20px;
            background: #f0f2f5;
            color: #333;
        }
        h1 {
            color: #2c3e50;
            border-bottom: 4px solid #3498db;
            padding-bottom: 15px;
            text-align: center;
            margin-bottom: 40px;
        }
        .main-container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 40px;
        }
        @media (max-width: 1000px) {
            .main-container {
                grid-template-columns: 1fr;
            }
        }
        .column {
            background: #fff;
            padding: 20px;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        }
        .column-header {
            background: #34495e;
            color: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            text-align: center;
            font-size: 1.2em;
            font-weight: bold;
        }
        .card {
            background: #fff;
            border: 1px solid #e1e4e8;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        .card:hover {
            transform: translateY(-3px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            border-color: #3498db;
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 10px;
        }
        .card h2 {
            color: #2c3e50;
            margin: 0;
            font-size: 16px;
            line-height: 1.4;
            flex: 1;
            margin-right: 10px;
        }
        .badge {
            display: inline-block;
            padding: 3px 8px;
            background: #e74c3c;
            color: white;
            border-radius: 12px;
            font-size: 11px;
            white-space: nowrap;
            font-weight: bold;
            text-transform: uppercase;
        }
        .links a {
            display: inline-block;
            padding: 6px 12px;
            background: #3498db;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            font-size: 13px;
            transition: background 0.2s;
        }
        .links a:hover {
            background: #2980b9;
        }
        .footer {
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            text-align: center;
            color: #7f8c8d;
            font-size: 0.9em;
        }
    </style>
</head>
<body>
    <h1>PaaS Infrastructure Automation - Diagram Index</h1>
    
    <div class="main-container">
        
        <!-- Column 1: Infrastructure Diagrams -->
        <div class="column">
            <div class="column-header">Infrastructure & Process Diagrams</div>
            <div class="grid">
''')

        for html_path in infra_diagrams:
            f.write(generate_card(html_path, html_path.stem))

        f.write('''            </div>
        </div>

        <!-- Column 2: Sequence Diagrams -->
        <div class="column">
            <div class="column-header">Sequence Diagrams</div>
            <div class="grid">
''')

        for html_path in sequence_diagrams:
            f.write(generate_card(html_path, html_path.stem))

        f.write('''            </div>
        </div>
    </div>

    <div class="footer">
        <p>Generated: <script>document.write(new Date().toLocaleString('en-US'))</script></p>
        <p>BME-VIK Thesis Project</p>
    </div>
</body>
</html>
''')

    print(f"✓ Index generated: {index_file}")
    print(f"\nOpen file://{index_file} in your browser")

if __name__ == "__main__":
    main()
