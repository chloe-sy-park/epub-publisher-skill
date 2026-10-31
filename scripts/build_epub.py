#!/usr/bin/env python3
"""Markdown -> EPUB3 via pandoc (Korean-friendly defaults), then EPUBCheck."""
import argparse, pathlib, shutil, subprocess, sys

HERE = pathlib.Path(__file__).resolve().parent

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("markdown")
    ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--title"); ap.add_argument("--author")
    ap.add_argument("--lang", default="ko")
    ap.add_argument("--cover", help="cover image path")
    ap.add_argument("--css", default=str(HERE.parent / "assets" / "ko.css"))
    ap.add_argument("--toc-depth", default="2")
    ap.add_argument("--no-check", action="store_true")
    a = ap.parse_args()
    if not shutil.which("pandoc"):
        sys.exit("pandoc not found (brew install pandoc)")
    cmd = ["pandoc", a.markdown, "-f", "markdown+smart", "-t", "epub3", "-o", a.output,
           "--toc", f"--toc-depth={a.toc_depth}", "--split-level=1",
           "--css", a.css, "-M", f"lang={a.lang}"]
    if a.title: cmd += ["-M", f"title={a.title}"]
    if a.author: cmd += ["-M", f"author={a.author}"]
    if a.cover: cmd += ["--epub-cover-image", a.cover]
    subprocess.run(cmd, check=True)
    print("built", a.output)
    if not a.no_check:
        sys.exit(subprocess.run([sys.executable, str(HERE / "check_epub.py"), a.output]).returncode)

main()
