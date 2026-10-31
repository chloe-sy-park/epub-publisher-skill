---
name: epub-publisher
description: 한글 원고(마크다운·Word·InDesign IDML·PDF)를 출판 품질 EPUB3로 만들고, 깨진 EPUB를 고치고, EPUBCheck로 검증한다. Use when the user wants to create, convert, repair, validate or finalize an EPUB / 전자책 / e-book, mentions Sigil, InDesign(.indd/.idml) or PDF-to-EPUB, or asks why an EPUB fails validation.
---

# EPUB Publisher

원고 → EPUB → 보정 → 검증 → (필요 시) Sigil 수작업 마무리. 모든 스크립트는 `~/.claude/skills/epub-publisher/scripts/`에 있고 Python 표준 라이브러리만 쓴다. 외부 도구는 `pandoc`, `epubcheck`(Java 필요)만 쓴다.

## 1. 입력 형식별 경로 (정확한 순서대로 고른다)

| 가진 것 | 경로 | 품질 |
|---|---|---|
| 마크다운 / Word(.docx) | `build_epub.py` (docx는 `pandoc in.docx -t markdown -o in.md` 후) | 가장 좋음 |
| InDesign `.indd` | **직접 변환 불가.** 인디자인에서 `내보내기 > EPUB(리플로우)` 또는 IDML로 내보내게 안내 | EPUB 내보내기가 최상 |
| IDML | `idml_to_md.py` → `build_epub.py` | 텍스트·제목만, 이미지·표·각주 수작업 |
| PDF | 마지막 수단. 아래 "PDF 주의" 참고 | 구조 손실 큼 |
| 이미 있는 EPUB(오류/조각남) | `fix_epub.py` | 보정 |

## 2. 명령

```bash
S=~/.claude/skills/epub-publisher/scripts

# 마크다운 -> EPUB (pandoc, 한글 CSS, H1=장 분할, 목차 자동, 끝에 EPUBCheck)
python3 $S/build_epub.py book.md -o book.epub --title "제목" --author "저자" [--cover cover.jpg] [--lang ko]

# IDML -> 마크다운 (스타일명으로 제목 판별; 안 맞으면 --map '내스타일=1')
python3 $S/idml_to_md.py book.idml -o book.md [--map 'ChapterTitle=1']

# 기존 EPUB 보정: nav 추가, NCX uid 일치, 언어, 메타데이터, 작은 장 병합, 목차 재생성
python3 $S/fix_epub.py in.epub -o out.epub --lang ko --title "제목" --author "저자" [--merge-min 1500]

# 검증 (영문 메시지, 오류가 있으면 종료코드 1)
python3 $S/check_epub.py out.epub
```

## 3. 항상 지킬 것 (시험에서 확인된 함정)

- **언어는 `ko`로 명시한다.** 변환기들이 한글 책에도 `en`을 넣는다. 저자가 `Unknown`이면 반드시 물어서 채운다.
- **완료 주장 전에 `check_epub.py`를 실제로 돌린다.** 변환 도구 자체의 PASS/완성도 수치는 믿지 않는다 (글자 11%만 남은 결과에도 PASS가 나왔다).
- `check_epub.py`는 EPUB 구조 적합성만 본다. **접근성(Ace)은 별도**이며 스토어 제출 시에만 필요하다고 안내한다.
- 변환 후 **글자 수를 원본과 대조**한다 (PDF는 `pymupdf`, 마크다운은 `wc -m`). 크게 줄면 실패로 보고한다.
- 사용자 원본 파일은 건드리지 않고 사본/별도 출력 경로에 쓴다. 외부 서비스(호스팅 검증기 등)에 원고를 올리지 않는다.

## 4. PDF 주의 (시험 결과)

- 합성 PDF에서는 본문이 ~11%만 남았고, 실제 한글 책 PDF 2권에서는 ~102% 보존됐다. 단 **장이 63~79조각**으로 쪼개지고 EPUBCheck 오류 2건(nav 없음, NCX uid 불일치)과 `㑄` 같은 따옴표 깨짐이 나왔다.
- 따라서 PDF 변환기 출력 → `fix_epub.py --merge-min 1500 --lang ko --author ...` → `check_epub.py` 순서로 처리하고, 목차와 깨진 문자를 사람이 훑어보게 한다.
- PDF 변환기는 `koreyba/Claude-Skill-pdf-to-epub`(MIT, `python -m scripts.convert in.pdf out.epub`, 의존성 pymupdf·pdfplumber·lxml·beautifulsoup4·Pillow·ebooklib)를 쓴다. 이 스킬에는 포함되어 있지 않다. 스캔본(OCR 필요)은 지원하지 않는다.
- 원고(마크다운/Word/IDML)가 있으면 PDF 경로를 쓰지 않는다.

## 5. Sigil 연계

Claude가 Sigil을 직접 조작하지는 못한다 (스킬/MCP 없음). 자동 처리 후 사람이 보정할 때 Sigil 앱에서 열도록 안내한다: 표지·이미지 교체, 목차(`도구 > 목차`) 확인, 단락별 서식. 반복 작업은 Sigil Python 플러그인으로 만들 수 있다 (Sigil 소스 `docs/Sigil_Plugin_Framework_rev15.epub` 참고).

## 6. 한계 (미검증)

- `idml_to_md.py`는 직접 만든 합성 IDML 1개로만 시험했다. 실제 인디자인 파일의 스타일명·다중 스토리 순서는 `--map`과 결과 확인이 필요하다.
- `fix_epub.py --merge-min`은 장 내부 제목 단계를 낮추지 않는다. 병합 후에도 목차는 h1–h2(`--toc-depth`)를 모두 나열한다.
- 리더 앱(Apple Books, 리디, 교보 등)에서의 실제 표시는 확인하지 않았다.
