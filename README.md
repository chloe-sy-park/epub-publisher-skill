# epub-publisher-skill

A [Claude Code](https://claude.com/claude-code) skill for turning manuscripts into valid EPUB3 files, with Korean text in mind.
한글 원고를 EPUB3로 만들고, 깨진 EPUB를 고치고, EPUBCheck로 검증하는 Claude Code 스킬입니다.

## What it does

| Input | Path |
|---|---|
| Markdown / Word | `build_epub.py` (pandoc) — Korean-friendly CSS, chapters split at H1, auto TOC, EPUBCheck at the end |
| InDesign IDML | `idml_to_md.py` → `build_epub.py` (text and headings only) |
| Existing / broken EPUB (e.g. from a PDF converter) | `fix_epub.py` — adds missing nav, syncs NCX uid, fixes language and metadata, merges tiny chapters, rebuilds the TOC |
| Any EPUB | `check_epub.py` — EPUBCheck summary, exit code 1 on errors |

`.indd` files cannot be read directly; export EPUB or IDML from InDesign first.

## Requirements

- Python 3 (standard library only)
- [pandoc](https://pandoc.org/) (for `build_epub.py`)
- [EPUBCheck](https://github.com/w3c/epubcheck) with Java (for `check_epub.py`)

```bash
brew install pandoc epubcheck
```

## Install

```bash
git clone https://github.com/chloe-sy-park/epub-publisher-skill ~/.claude/skills/epub-publisher
```

Restart Claude Code; the skill triggers on requests about creating, converting, repairing or validating EPUB / 전자책.

## Usage

```bash
S=~/.claude/skills/epub-publisher/scripts
python3 $S/build_epub.py book.md -o book.epub --title "Title" --author "Author"
python3 $S/idml_to_md.py book.idml -o book.md --map 'ChapterTitle=1'
python3 $S/fix_epub.py in.epub -o out.epub --lang ko --author "Author" --merge-min 1500
python3 $S/check_epub.py out.epub
```

## Tested / not tested

- Tested: `fix_epub.py` on an EPUB produced by a PDF converter (2 EPUBCheck errors, 79 chapter files → 0 errors, 8 files); `idml_to_md.py` + `build_epub.py` on a small synthetic IDML.
- Not tested: real InDesign exports, rendering in reader apps (Apple Books, Kobo, etc.).
- Known limits: images, tables and footnotes are not converted from IDML; `--merge-min` does not demote heading levels; accessibility (Ace) checks are out of scope.

## Notes on PDF input

PDF-to-EPUB conversion is a last resort. In our tests a third-party converter ([koreyba/Claude-Skill-pdf-to-epub](https://github.com/koreyba/Claude-Skill-pdf-to-epub), MIT) kept ~102% of the text on two real Korean book PDFs, but split chapters into dozens of tiny files and produced EPUBs that failed EPUBCheck; run its output through `fix_epub.py`. It is not bundled here.

## License

MIT
