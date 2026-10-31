#!/usr/bin/env python3
"""InDesign IDML -> Markdown (stdlib only).

Headings come from paragraph style names. Default mapping matches names like
'H1', 'Heading 2', '제목1', '장제목'; override with --map style=level (e.g. --map 'Chapter Title=1').
Story order follows designmap.xml; check it matches reading order for multi-story layouts.
"""
import argparse, re, sys, zipfile
import xml.etree.ElementTree as ET

def level_for(style, custom):
    name = style.split("/")[-1].replace("%20", " ")
    if name in custom: return custom[name]
    m = re.search(r"(?:^|[^a-z])(?:h|heading|title|제목|소제목)\s*([1-4])\b", name, re.I)
    if m: return int(m.group(1))
    if re.search(r"장\s*제목|chapter", name, re.I): return 1
    return 0

def story_text(root, custom):
    out = []
    for para in root.iter("ParagraphStyleRange"):
        parts = []
        for el in para.iter():
            if el.tag == "Content" and el.text: parts.append(el.text)
            elif el.tag == "Br": parts.append("\n")
        text = "".join(parts).replace(" ", " ").replace("﻿", "")
        for line in text.split("\n"):
            line = line.strip()
            if not line: continue
            lvl = level_for(para.get("AppliedParagraphStyle", ""), custom)
            out.append(("#" * lvl + " " + line) if lvl else line)
    return "\n\n".join(out)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("idml"); ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--map", action="append", default=[], help="StyleName=level (0 = body)")
    a = ap.parse_args()
    custom = {k: int(v) for k, v in (m.split("=", 1) for m in a.map)}
    with zipfile.ZipFile(a.idml) as z:
        dm = z.read("designmap.xml").decode("utf-8")
        srcs = re.findall(r'<idPkg:Story[^>]*src="([^"]+)"', dm) or sorted(n for n in z.namelist() if n.startswith("Stories/"))
        chunks = [story_text(ET.fromstring(z.read(s)), custom) for s in srcs]
        links = sorted({n for n in z.namelist() if n.startswith("Resources/")})
    md = "\n\n".join(c for c in chunks if c.strip()) + "\n"
    open(a.output, "w", encoding="utf-8").write(md)
    heads = len(re.findall(r"^#+ ", md, re.M))
    print(f"{len(srcs)} stories, {heads} headings, {len(md)} chars -> {a.output}")
    if not heads: print("WARN: no headings found; pass --map 'YourStyle=1'", file=sys.stderr)
    print("NOTE: images/tables/footnotes are not converted; re-add images in the markdown.")

main()
