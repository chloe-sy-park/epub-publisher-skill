#!/usr/bin/env python3
"""Repair an existing EPUB (stdlib only).

Fixes: missing nav document, NCX/OPF identifier mismatch, wrong language,
placeholder metadata, and optionally merges tiny chapter files. The TOC
(nav.xhtml + toc.ncx) is rebuilt from the headings actually in the spine.
"""
import argparse, html, os, re, shutil, sys, tempfile, zipfile
import xml.etree.ElementTree as ET

NS = {"opf": "http://www.idpf.org/2007/opf", "dc": "http://purl.org/dc/elements/1.1/",
      "c": "urn:oasis:names:tc:opendocument:xmlns:container"}
for k, v in (("", NS["opf"]), ("dc", NS["dc"])):
    ET.register_namespace(k, v)

def text_len(xhtml):
    m = re.search(r"<body[^>]*>(.*)</body>", xhtml, re.S)
    return len(re.sub(r"<[^>]+>|\s+", "", m.group(1) if m else xhtml))

def body_inner(xhtml):
    m = re.search(r"<body[^>]*>(.*)</body>", xhtml, re.S)
    return m.group(1) if m else xhtml

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("epub"); ap.add_argument("-o", "--output", required=True)
    ap.add_argument("--lang"); ap.add_argument("--title"); ap.add_argument("--author")
    ap.add_argument("--merge-min", type=int, default=0,
                    help="keep appending following files to a chapter until it holds at least this many visible chars")
    ap.add_argument("--toc-depth", type=int, default=2)
    a = ap.parse_args()

    tmp = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(a.epub) as z:
            z.extractall(tmp)
        cont = ET.parse(os.path.join(tmp, "META-INF", "container.xml"))
        opf_rel = cont.find(".//c:rootfile", NS).get("full-path")
        opf_path = os.path.join(tmp, opf_rel); base = os.path.dirname(opf_path)
        tree = ET.parse(opf_path); pkg = tree.getroot()
        meta = pkg.find("opf:metadata", NS); man = pkg.find("opf:manifest", NS); spine = pkg.find("opf:spine", NS)
        items = {i.get("id"): i for i in man.findall("opf:item", NS)}
        log = []

        # --- metadata
        def setdc(tag, val):
            el = meta.find(f"dc:{tag}", NS)
            if el is None:
                el = ET.SubElement(meta, f"{{{NS['dc']}}}{tag}")
            if el.text != val:
                log.append(f"{tag}: {el.text!r} -> {val!r}"); el.text = val
        if a.lang: setdc("language", a.lang)
        if a.title: setdc("title", a.title)
        if a.author: setdc("creator", a.author)
        lang = meta.find("dc:language", NS).text or "en"
        uid_ref = pkg.get("unique-identifier")
        uid = next((e.text for e in meta.findall("dc:identifier", NS) if e.get("id") == uid_ref), None) \
            or meta.find("dc:identifier", NS).text
        if (meta.find("dc:creator", NS) is None) or meta.find("dc:creator", NS).text in (None, "Unknown"):
            print("WARN: author is missing/'Unknown' (use --author)", file=sys.stderr)

        # --- spine documents
        order = [r.get("idref") for r in spine.findall("opf:itemref", NS)]
        docs = [i for i in order if items.get(i) is not None
                and items[i].get("media-type") == "application/xhtml+xml"
                and "nav" not in (items[i].get("properties") or "")]
        path = lambda i: os.path.join(base, items[i].get("href"))
        rd = lambda i: open(path(i), encoding="utf-8").read()

        # --- optional merge of tiny files
        remap = {}
        if a.merge_min:
            keep, glen = [], 0
            for i in docs:
                if keep and glen < a.merge_min:
                    glen += text_len(rd(i))
                    prev = keep[-1]; ptxt = rd(prev)
                    ptxt = re.sub(r"</body>", lambda m: body_inner(rd(i)) + "\n</body>", ptxt, count=1)
                    open(path(prev), "w", encoding="utf-8").write(ptxt)
                    remap[items[i].get("href")] = items[prev].get("href")
                    os.remove(path(i)); man.remove(items[i])
                    for r in spine.findall("opf:itemref", NS):
                        if r.get("idref") == i: spine.remove(r)
                else:
                    keep.append(i); glen = text_len(rd(i))
            log.append(f"merged {len(docs) - len(keep)} small files ({len(docs)} -> {len(keep)})")
            docs = keep

        # --- rewrite lang + links in every xhtml
        for i in docs:
            t = rd(i)
            def fixhtml(m):
                tag = m.group(0)
                for attr in ("lang", "xml:lang"):
                    if re.search(rf'\s{attr}="', tag):
                        tag = re.sub(rf'(\s{attr}=")[^"]*"', rf'\g<1>{lang}"', tag)
                    else:
                        tag = tag[:-1] + f' {attr}="{lang}">'
                return tag
            t = re.sub(r"<html[^>]*>", fixhtml, t, count=1)
            for old, new in remap.items():
                t = t.replace(old, new)
            # --- headings -> ids
            open(path(i), "w", encoding="utf-8").write(t)

        # --- TOC entries from real headings
        entries, n = [], 0
        for i in docs:
            t = rd(i); href = items[i].get("href")
            def addid(m):
                nonlocal n
                lvl, attrs, inner = int(m.group(1)), m.group(2), m.group(3)
                if lvl > a.toc_depth: return m.group(0)
                label = html.unescape(re.sub(r"<[^>]+>", "", inner)).strip()
                if not label: return m.group(0)
                idm = re.search(r'\sid="([^"]+)"', attrs)
                if not idm:
                    n += 1; hid = f"toc-h{n}"; attrs += f' id="{hid}"'
                else:
                    hid = idm.group(1)
                entries.append((lvl, label, f"{href}#{hid}"))
                return f"<h{lvl}{attrs}>{inner}</h{lvl}>"
            t2 = re.sub(r"<h([1-6])([^>]*)>(.*?)</h\1>", addid, t, flags=re.S)
            if t2 != t: open(path(i), "w", encoding="utf-8").write(t2)
        if not entries:
            entries = [(1, items[i].get("href"), items[i].get("href")) for i in docs]
        top = min(e[0] for e in entries)
        esc = lambda s: html.escape(s, quote=False)

        # --- nav.xhtml
        nav_item = next((i for i in man.findall("opf:item", NS) if "nav" in (i.get("properties") or "").split()), None)
        if nav_item is None:
            nav_item = ET.SubElement(man, f"{{{NS['opf']}}}item",
                                     {"id": "nav", "href": "nav.xhtml", "media-type": "application/xhtml+xml", "properties": "nav"})
            log.append("added nav.xhtml")
        def nested(ents):
            html_, stack = "", []
            for k, (lvl, label, href) in enumerate(ents):
                d = lvl - top + 1
                if k:
                    pd = ents[k - 1][0] - top + 1
                    if d > pd: html_ += "\n<ol>"; stack.append(1)
                    else:
                        html_ += "</li>"
                        for _ in range(pd - d): html_ += "\n</ol></li>"
                html_ += f'\n<li><a href="{href}">{esc(label)}</a>'
            last = ents[-1][0] - top + 1
            html_ += "</li>" + "\n</ol></li>" * (last - 1)
            return "<ol>" + html_ + "\n</ol>"
        nav = ('<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE html>\n'
               f'<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" lang="{lang}" xml:lang="{lang}">\n'
               '<head><meta charset="UTF-8"/><title>Contents</title></head>\n<body>\n'
               f'<nav epub:type="toc" id="toc"><h1>Contents</h1>\n{nested(entries)}\n</nav>\n</body>\n</html>\n')
        open(os.path.join(base, nav_item.get("href")), "w", encoding="utf-8").write(nav)

        # --- toc.ncx (EPUB2 compat), uid synced to OPF identifier
        ncx_item = next((i for i in man.findall("opf:item", NS) if i.get("media-type") == "application/x-dtbncx+xml"), None)
        if ncx_item is not None:
            pts = "".join(
                f'<navPoint id="np{k}" playOrder="{k}"><navLabel><text>{esc(l)}</text></navLabel><content src="{h}"/></navPoint>\n'
                for k, (_, l, h) in enumerate(entries, 1))
            title = meta.find("dc:title", NS).text or ""
            ncx = ('<?xml version="1.0" encoding="UTF-8"?>\n<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">\n'
                   f'<head><meta name="dtb:uid" content="{html.escape(uid)}"/><meta name="dtb:depth" content="{a.toc_depth}"/>'
                   '<meta name="dtb:totalPageCount" content="0"/><meta name="dtb:maxPageNumber" content="0"/></head>\n'
                   f'<docTitle><text>{esc(title)}</text></docTitle>\n<navMap>\n{pts}</navMap>\n</ncx>\n')
            open(os.path.join(base, ncx_item.get("href")), "w", encoding="utf-8").write(ncx)
            log.append("rebuilt toc.ncx with matching uid")

        tree.write(opf_path, encoding="utf-8", xml_declaration=True)
        # --- rezip: mimetype first, stored
        with zipfile.ZipFile(a.output, "w") as z:
            z.write(os.path.join(tmp, "mimetype"), "mimetype", compress_type=zipfile.ZIP_STORED)
            for root, _, files in os.walk(tmp):
                for f in sorted(files):
                    full = os.path.join(root, f); rel = os.path.relpath(full, tmp)
                    if rel != "mimetype":
                        z.write(full, rel, compress_type=zipfile.ZIP_DEFLATED)
        log.append(f"TOC entries: {len(entries)}")
        print("\n".join(log)); print("wrote", a.output)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

main()
