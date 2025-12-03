import argparse
import sys
from typing import List, Optional
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Wrap Mermaid markdown files into HTML.")
    parser.add_argument(
        "input_path",
        nargs="?",
        help="Optional path to a single markdown file. Defaults to all files in ./source.",
    )
    parser.add_argument(
        "-n",
        "--name",
        help="Custom output filename (without suffix). Only valid when processing one file.",
    )
    parser.add_argument(
        "-d",
        "--dark",
        action="store_true",
        help="Enable dark mode output.",
    )
    parser.add_argument(
        "-i",
        "--input-dir",
        default="source",
        help="Directory containing source markdown files.",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default="output",
        help="Directory to write output HTML files.",
    )
    return parser.parse_args()


def extract_mermaid(content: str) -> str:
    lines = content.splitlines()
    start = None
    end = None

    for idx, line in enumerate(lines):
        if line.strip().startswith("```"):
            start = idx
            break

    if start is not None:
        for idx in range(len(lines) - 1, start, -1):
            if lines[idx].strip().startswith("```"):
                end = idx
                break

        if end is not None and end > start:
            return "\n".join(lines[start + 1 : end]).strip()

    return "\n".join(lines).strip()


def indent_mermaid(mermaid_code: str) -> str:
    lines = mermaid_code.splitlines()
    if not lines:
        return "            "
    return "\n".join(f"            {line}" for line in lines)


def theme_settings(use_dark: bool) -> dict:
    if use_dark:
        return {
            "theme": "dark",
            "bg_color": "#1e1e1e",
            "text_color": "#f5f5f5",
            "suffix": "_dark",
        }
    return {
        "theme": "default",
        "bg_color": "#ffffff",
        "text_color": "#333333",
        "suffix": "_light",
    }


def load_template(template_path: Path) -> str:
    try:
        return template_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        sys.exit(f"Template not found: {template_path}")


def collect_targets(base_dir: Path, source_dir: Path, input_path: Optional[str]) -> List[Path]:
    if input_path:
        candidate = Path(input_path)
        if not candidate.is_absolute():
            candidate = base_dir / candidate
        if not candidate.exists():
            sys.exit(f"Input file not found: {candidate}")
        return [candidate]

    md_files = sorted(source_dir.glob("*.md"))
    if not md_files:
        print(f"No .md files found in {source_dir}")
    return md_files


def main() -> None:
    args = parse_args()
    base_dir = Path.cwd()  # Use CWD so relative paths work as expected from where the user runs it
    
    source_dir = Path(args.input_dir)
    if not source_dir.is_absolute():
        source_dir = base_dir / source_dir

    output_dir = Path(args.output_dir)
    if not output_dir.is_absolute():
        output_dir = base_dir / output_dir

    # Template is still expected in the script directory usually, or maybe relative to CWD?
    # Let's assume it's in the same dir as the script for now.
    script_dir = Path(__file__).parent
    template_path = script_dir / "template.html"

    source_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    template = load_template(template_path)
    targets = collect_targets(base_dir, source_dir, args.input_path)

    if not targets:
        return

    if args.name and len(targets) != 1:
        sys.exit("--name can only be used when converting a single file.")

    theme = theme_settings(args.dark)

    for md_path in targets:
        content = md_path.read_text(encoding="utf-8")
        mermaid_raw = extract_mermaid(content)
        mermaid_block = indent_mermaid(mermaid_raw)

        base_name = args.name if args.name else md_path.stem
        title = base_name
        output_file = output_dir / f"{base_name}{theme['suffix']}.html"

        replacements = {
            "{title}": title,
            "{theme}": theme["theme"],
            "{bg_color}": theme["bg_color"],
            "{text_color}": theme["text_color"],
            "{mermaid_code}": mermaid_block,
        }

        html = template
        for placeholder, value in replacements.items():
            html = html.replace(placeholder, value)

        output_file.write_text(html, encoding="utf-8")
        print(f"Generated: {output_file}")


if __name__ == "__main__":
    main()
