#!/usr/bin/env python3
"""Run EPUBCheck on a file and print a short English summary. Exit 0 = no errors."""
import re, shutil, subprocess, sys

def main():
    if len(sys.argv) != 2:
        sys.exit("usage: check_epub.py book.epub")
    exe = shutil.which("epubcheck")
    if not exe:
        sys.exit("epubcheck not found (brew install epubcheck)")
    p = subprocess.run([exe, "--locale", "en", sys.argv[1]], capture_output=True, text=True)
    out = p.stdout + p.stderr
    issues = [l.strip() for l in out.splitlines() if re.match(r"\s*(ERROR|FATAL|WARNING)\(", l)]
    for l in issues:
        print(l[:240])
    m = re.search(r"Messages:.*", out)
    print(m.group(0) if m else out.strip().splitlines()[-1] if out.strip() else "no output")
    sys.exit(1 if any(l.startswith(("ERROR", "FATAL")) for l in issues) else 0)

main()
