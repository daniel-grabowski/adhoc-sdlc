#!/usr/bin/env python3
"""Read-side dla adhoc-sdlc: parser dokumentu, scoring i builder context pack.

Ten moduł jest jedynym miejscem, które CZYTA treść plików adhoc-sdlc/ pod kątem
sekcji. Komendy slash nigdy nie skanują markdownów same — wołają helper, który
przez ten moduł buduje ograniczony, jawny context pack dla agenta.

Czyste funkcje string->struktura (poza fasadą I/O extract_document). Stdlib-only.
"""

from __future__ import annotations

import datetime as dt
import json
import math
import re
import time
from collections import Counter
from pathlib import Path


# Odporność na transient OSError przy odczycie (EIO na WSL 9P /mnt/c). Łączny
# czas czekania w najgorszym razie ~2.5 s/plik (0.5 + 2.0), potem skip + raport.
READ_ATTEMPTS = 3
READ_DELAYS = (0.5, 2.0)


# Placeholdery z szablonów body helpera (plan/execute/handoff). Sekcja, której
# treść to wyłącznie placeholder (albo pustka), nie niesie faktów dla agenta.
PLACEHOLDERS = ("TODO", "None yet.", "Not run yet.", "Pending.")

# Nagłówek poziomu 2: dokładnie '##' + spacja (NIE '###' i głębsze).
HEADING2_RE = re.compile(r"^##(?!#)\s+(.*)$")
# Otwarcie/zamknięcie bloku kodu (fence). Wewnątrz '##' nie jest nagłówkiem.
FENCE_RE = re.compile(r"^\s*(```|~~~)")


def _unesc(value: str) -> str:
    return value.replace('\\"', '"').replace("\\\\", "\\")


def _as_list(value) -> list[str]:
    """Wymusza listę stringów dla keywords (defensywnie wobec uszkodzonego frontmatter).

    None/'' -> []; string (np. `keywords: foo` bez nawiasów) -> [string], NIE iteracja po
    znakach (inaczej _jaccard liczyłby wspólne litery); lista -> elementy jako string bez pustych.
    """
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    return [str(value)]


def _parse_fm_block(block: str) -> dict:
    """Parsuje wnętrze bloku frontmatter (bez znaczników ---) na dict metadanych."""
    meta: dict = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, _, raw = line.partition(":")
        key = key.strip()
        raw = raw.strip()
        if raw.startswith("[") and raw.endswith("]"):
            inner = raw[1:-1].strip()
            meta[key] = [tok.strip() for tok in inner.split(",") if tok.strip()] if inner else []
        elif raw.startswith('"') and raw.endswith('"') and len(raw) >= 2:
            meta[key] = _unesc(raw[1:-1])
        else:
            meta[key] = raw
    return meta


def split_frontmatter(text: str) -> tuple[dict, str]:
    """Zwraca (meta, body). Body to treść po zamykającym '---'. Brak frontmatter -> ({}, text)."""
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text
    meta = _parse_fm_block(text[4:end])
    after = end + len("\n---")
    nl = text.find("\n", after)
    body = "" if nl == -1 else text[nl + 1:]
    return meta, body


def is_placeholder(text: str) -> bool:
    """True gdy treść jest pusta albo to dokładnie jeden ze znanych placeholderów."""
    stripped = text.strip()
    return stripped == "" or stripped in PLACEHOLDERS


def parse_sections(body: str) -> list[dict]:
    """Dzieli body na sekcje po nagłówkach poziomu 2.

    - '###' i głębsze zostają treścią sekcji nadrzędnej (nie tworzą pozycji);
    - '##' wewnątrz bloku ``` / ~~~ nie jest nagłówkiem;
    - tekst przed pierwszym '## ' -> sekcja preamble (heading='');
    - pusta preamble jest pomijana.
    Zwraca [{'heading', 'level', 'text', 'is_placeholder'}].
    """
    normalized = body.replace("\r\n", "\n").replace("\r", "\n")
    lines = normalized.split("\n")

    sections: list[dict] = []
    cur_heading = ""
    cur_level = 0
    cur_lines: list[str] = []
    in_fence = False

    def flush() -> None:
        text = "\n".join(cur_lines).strip()
        if cur_heading != "" or text != "":
            sections.append({
                "heading": cur_heading,
                "level": cur_level,
                "text": text,
                "is_placeholder": is_placeholder(text),
            })

    for line in lines:
        if FENCE_RE.match(line):
            in_fence = not in_fence
            cur_lines.append(line)
            continue
        if not in_fence:
            match = HEADING2_RE.match(line)
            if match:
                flush()
                cur_heading = match.group(1).strip()
                cur_level = 2
                cur_lines = []
                continue
        cur_lines.append(line)

    flush()
    return sections


def get_section(sections: list[dict], heading: str) -> dict | None:
    """Pierwsza sekcja o danym nagłówku (porównanie case-insensitive) albo None."""
    target = heading.strip().lower()
    for section in sections:
        if section["heading"].strip().lower() == target:
            return section
    return None


def append_to_section(body: str, heading: str, new_lines: list[str]) -> str | None:
    """Wstawia new_lines na koniec sekcji `heading` (przed następnym nagłówkiem ## ).

    Fence-aware (## w bloku ``` ignorowane). Nie przebudowuje reszty body -
    pozostałe linie zostają bajtowo nienaruszone. Zwraca None gdy brak sekcji.
    """
    lines = body.split("\n")
    target = heading.strip().lower()

    in_fence = False
    start = None
    for index, line in enumerate(lines):
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence:
            match = HEADING2_RE.match(line)
            if match and match.group(1).strip().lower() == target:
                start = index
                break
    if start is None:
        return None

    in_fence = False
    end = len(lines)
    for index in range(start + 1, len(lines)):
        line = lines[index]
        if FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if not in_fence and HEADING2_RE.match(line):
            end = index
            break

    lines[end:end] = new_lines
    return "\n".join(lines)


def validate_document(meta: dict, sections: list[dict]) -> list[str]:
    """Lista ostrzeżeń (nie wyjątków) dla read-side: zasila warnings[] w packu."""
    warnings: list[str] = []
    if not meta:
        warnings.append("no_frontmatter")
    body_sections = [s for s in sections if s["heading"] != ""]
    if body_sections and all(s["is_placeholder"] for s in body_sections):
        warnings.append("all_placeholder")
    return warnings


# --- Scoring relevance (deterministyczny, bez LLM) ---------------------------

WEIGHT_KEYWORD = 0.45
WEIGHT_PROJECT = 0.25
WEIGHT_NAME = 0.15
WEIGHT_RECENCY = 0.15
RECENCY_HALF_WINDOW_DAYS = 90


def _stem_kw(token: str) -> str:
    """Lekka normalizacja liczby mnogiej do matchowania keywords.

    Usuwa pojedyncze końcowe 's' (colors->color, skins->skin), chroni 'ss' (css,
    class, less) i krótkie tokeny (len<=3: is, as, css). Stosowana TYLKO do porównań
    (jaccard/overlap/bramka), nigdy do wyświetlania keywords w raporcie.
    """
    t = token.lower()
    if len(t) > 3 and t.endswith("s") and not t.endswith("ss"):
        return t[:-1]
    return t


def _norm_kw(tokens) -> set:
    """Zbiór znormalizowanych tokenów (dedup po rdzeniu) dla porównań keywords."""
    return {_stem_kw(t) for t in (tokens or [])}


def _jaccard(a, b) -> float:
    set_a, set_b = set(a), set(b)
    union = set_a | set_b
    if not union:
        return 0.0
    return len(set_a & set_b) / len(union)


def _name_component(rec_name: str, query_name: str) -> float:
    a = (rec_name or "").strip().lower()
    b = (query_name or "").strip().lower()
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if b in a or a in b:
        return 0.5
    return 0.0


def _recency_component(rec: dict, today_iso: str) -> float:
    raw = rec.get("updated") or rec.get("created") or ""
    if not raw:
        return 0.0
    try:
        date = dt.datetime.fromisoformat(raw)
        today = dt.datetime.fromisoformat(today_iso)
    except ValueError:
        return 0.0
    age_days = (today - date).days
    if age_days < 0:
        age_days = 0
    return max(0.0, 1.0 - age_days / RECENCY_HALF_WINDOW_DAYS)


def score_record(rec: dict, query: dict, today_iso: str) -> float:
    """Trafność rekordu 0..1. Nieaktywny sygnał (brak w query) -> waga redystrybuowana.

    Recency jest aktywne zawsze, więc przy pustym query score = świeżość rekordu.
    """
    components: list[tuple[float, float]] = []

    q_keywords = query.get("keywords") or []
    q_project = (query.get("project") or "").strip()
    q_name = (query.get("name") or "").strip()

    if q_keywords:
        components.append((WEIGHT_KEYWORD, _jaccard(_norm_kw(q_keywords), _norm_kw(rec.get("keywords")))))
    if q_project:
        match = 1.0 if rec.get("project", "") == q_project else 0.0
        components.append((WEIGHT_PROJECT, match))
    if q_name:
        components.append((WEIGHT_NAME, _name_component(rec.get("name", ""), q_name)))
    components.append((WEIGHT_RECENCY, _recency_component(rec, today_iso)))

    denom = sum(weight for weight, _ in components)
    if denom == 0:
        return 0.0
    score = sum(weight * value for weight, value in components) / denom
    return round(score, 3)


def _read_text(path) -> str:
    """Czyta plik z ponawianiem na transient OSError (EIO). Po wyczerpaniu prób re-raise."""
    last_err: OSError | None = None
    for attempt in range(READ_ATTEMPTS):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return handle.read()
        except OSError as err:
            last_err = err
            if attempt < len(READ_DELAYS):
                time.sleep(READ_DELAYS[attempt])
    raise last_err  # type: ignore[misc]


_JSON_META_KEYS = ("type", "name", "title", "project", "keywords", "created", "updated", "status")


def task_summary(data: dict) -> dict | None:
    """Stan zadań dziennika schema 2: {schema, items, open, in_progress}. Dziennik bez pola
    schema (tryb dawny) nie prowadzi zadań -> None."""
    if not isinstance(data, dict) or "schema" not in data:
        return None
    items = []
    for t in (data.get("tasks") or []):
        if isinstance(t, dict):
            item = {"id": str(t.get("id", "")), "title": str(t.get("title", "")),
                    "status": str(t.get("status", "")), "source": str(t.get("source", ""))}
            if t.get("ref"):
                item["ref"] = str(t["ref"])
            items.append(item)
    return {
        "schema": data.get("schema"),
        "items": items,
        "open": [t["id"] for t in items if t["status"] != "done"],
        "in_progress": next((t["id"] for t in items if t["status"] == "in_progress"), None),
    }


def _extract_execute_json(path) -> dict:
    """Czyta execute-*.json (helper jest jego jedynym writerem) i mapuje na model dokumentu.

    JSON to natywny format dziennika wykonania. Żeby reszta read-side (EXTRACT_MAP, scoring,
    pack) działała bez rozgałęzień, budujemy z niego SYNTETYCZNE sekcje o tych samych nazwach
    nagłówków co stary markdown (Steps/Decisions And Deviations/Verification/Final Result), plus
    nowość ponad markdownem: `touched_files` zagregowane i zdeduplikowane z entries[].files.
    Niepoprawny JSON nie wywraca packa - zwraca warning `invalid_json` i jest pomijany dalej.
    """
    raw = _read_text(path)
    try:
        data = json.loads(raw)
    except ValueError:
        return {"path": str(path), "meta": {}, "sections": [], "warnings": ["invalid_json"], "touched_files": [],
                "tasks": None}

    meta = {k: data.get(k, "") for k in _JSON_META_KEYS}
    meta["keywords"] = _as_list(data.get("keywords"))
    entries = data.get("entries", []) or []

    step_lines = []
    for e in entries:
        ts = e.get("ts", "")
        phase = (e.get("phase") or "").strip()
        prefix = f"[{phase}] " if phase else ""
        step_lines.append(f"- {ts}: {prefix}{e.get('note', '')}".rstrip())
    steps_text = "\n".join(step_lines)

    dec_text = "\n".join(
        (d.get("text", "") if isinstance(d, dict) else str(d)) for d in (data.get("decisions") or [])
    ).strip()

    ver_lines = []
    for v in (data.get("verification") or []):
        if isinstance(v, dict):
            cmd, out = v.get("command", ""), v.get("outcome", "")
            ver_lines.append(f"{cmd} => {out}" if cmd else out)
        else:
            ver_lines.append(str(v))
    ver_text = "\n".join(x for x in ver_lines if x).strip()

    final = data.get("final_result") or ""
    op_text = (data.get("original_prompt") or "").strip()
    sections = [
        {"heading": "Original Prompt", "level": 2, "text": op_text, "is_placeholder": op_text == ""},
        {"heading": "Steps", "level": 2, "text": steps_text, "is_placeholder": steps_text == ""},
        {"heading": "Decisions And Deviations", "level": 2, "text": dec_text, "is_placeholder": dec_text == ""},
        {"heading": "Verification", "level": 2, "text": ver_text, "is_placeholder": ver_text == ""},
        {"heading": "Final Result", "level": 2, "text": final, "is_placeholder": final == ""},
    ]
    # Syntetyczna sekcja Tasks tylko dla dziennika schema 2 (dawny dziennik bez zmian kształtu).
    tasks = task_summary(data)
    if tasks is not None:
        task_text = "\n".join(f"- [{t['id']}] ({t['status']}) {t['title']}" for t in tasks["items"])
        sections.append({"heading": "Tasks", "level": 2, "text": task_text, "is_placeholder": task_text == ""})

    seen, touched = set(), []
    for e in entries:
        for f in (e.get("files") or []):
            p = (f.get("path", "") if isinstance(f, dict) else str(f)).strip()
            if p and p not in seen:
                seen.add(p)
                touched.append({"path": p, "change": (f.get("change", "") if isinstance(f, dict) else "")})

    return {"path": str(path), "meta": meta, "sections": sections, "warnings": [], "touched_files": touched,
            "tasks": tasks}


def extract_document(path) -> dict:
    """Fasada I/O: czyta plik (z retry) i zwraca {path, meta, sections, warnings, touched_files}."""
    if str(path).endswith(".json"):
        return _extract_execute_json(path)
    text = _read_text(path)
    meta, body = split_frontmatter(text)
    sections = parse_sections(body)
    warnings = validate_document(meta, sections)
    return {"path": str(path), "meta": meta, "sections": sections, "warnings": warnings, "touched_files": []}


# --- Read model + builder context pack ---------------------------------------

KIND_PREFIXES = ("plan", "execute", "handoff")
FILENAME_RE = re.compile(r"^(plan|execute|handoff)-(\d{4}-\d{2}-\d{2}(?:-\d{6})?)-(.+)\.(?:md|json)$")

# Mapowanie "pole logiczne -> fizyczna sekcja" per typ (history extracts).
EXTRACT_MAP = {
    "plan": ["Summary"],
    "execute": ["Final Result", "Decisions And Deviations"],
    "handoff": ["Goal", "Next Steps"],
}
# Sekcje wyciągane dla wybranego handoffu w resume (detail mode).
RESUME_EXTRACT = ["Goal", "Next Steps", "What Worked", "What Didn't Work"]

BUDGETS = {
    "history": {"max_items": 7, "max_extracts_per_item": 2, "max_extract_chars": 600, "max_total_chars": 12000},
    "resume": {"max_handoffs": 4, "max_related_items": 5, "max_extract_chars": 600, "max_total_chars": 10000},
    "handoff": {"max_related_items": 5, "max_total_chars": 10000},
}

_PUBLIC_KEYS = ("path", "type", "name", "title", "project", "keywords",
                "created", "updated", "status", "score", "sections", "extracts", "touched_files")


def load_records(root) -> tuple[list[dict], dict]:
    """Skanuje root/adhoc-sdlc -> (rekordy, skipped).

    Nieczytelny plik (OSError po wyczerpaniu retry) jest pomijany i zapisany w
    skipped['unreadable'] — pojedynczy zły plik nie wywraca całego packa.
    Plik bez frontmatter (stary korpus) jest ładowany z gracją (fallback po nazwie
    pliku) ale raportowany w skipped['incomplete'].
    """
    base = Path(root) / "adhoc-sdlc"
    records: list[dict] = []
    skipped: dict = {"unreadable": [], "incomplete": []}
    if not base.is_dir():
        return records, skipped
    # Markdown dla wszystkich typów (plan/handoff oraz stare execute) + natywny JSON dla execute.
    paths: list[Path] = []
    for prefix in KIND_PREFIXES:
        paths.extend(sorted(base.glob(f"{prefix}-*.md")))
    paths.extend(sorted(base.glob("execute-*.json")))
    for path in paths:
        try:
            doc = extract_document(path)
        except OSError:
            skipped["unreadable"].append(str(path))
            continue
        if "invalid_json" in doc["warnings"]:
            skipped["unreadable"].append(str(path))
            continue
        if "no_frontmatter" in doc["warnings"]:
            skipped["incomplete"].append(str(path))
        meta = doc["meta"]
        fm = FILENAME_RE.match(path.name)
        records.append({
            "path": str(path),
            "type": meta.get("type") or (fm.group(1) if fm else ""),
            "name": meta.get("name") or (fm.group(3) if fm else path.stem),
            "title": meta.get("title", ""),
            "project": meta.get("project", ""),
            "keywords": _as_list(meta.get("keywords")),
            "created": meta.get("created", ""),
            "updated": meta.get("updated", meta.get("created", "")) or "",
            "status": meta.get("status", ""),
            "score": 0.0,
            "sections": [{"heading": s["heading"], "is_placeholder": s["is_placeholder"]}
                         for s in doc["sections"] if s["heading"] != ""],
            "extracts": [],
            "touched_files": doc.get("touched_files", []),
            "_sections_full": doc["sections"],
            "_tasks": doc.get("tasks"),
        })
    return records, skipped


def _age_days(rec: dict, today_iso: str) -> int | None:
    raw = rec.get("updated") or rec.get("created") or ""
    if not raw:
        return None
    try:
        date = dt.datetime.fromisoformat(raw)
        today = dt.datetime.fromisoformat(today_iso)
    except ValueError:
        return None
    return (today - date).days


def _in_scope(rec: dict, project: str, days, today_iso: str) -> bool:
    if project and rec.get("project", "") != project:
        return False
    if days is not None:
        age = _age_days(rec, today_iso)
        if age is None or age > days:
            return False
    return True


def _truncate(text: str, max_chars: int) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    limit = max_chars - 1  # miejsce na "…"
    cut = text[:limit]
    space = cut.rfind(" ")
    if space > limit // 2:
        cut = cut[:space]
    return cut.rstrip() + "…", True


def _build_extracts(rec: dict, headings: list[str], max_extracts: int, max_extract_chars: int) -> list[dict]:
    extracts: list[dict] = []
    for heading in headings:
        if len(extracts) >= max_extracts:
            break
        section = get_section(rec["_sections_full"], heading)
        if section is None or section["is_placeholder"]:
            continue
        text, truncated = _truncate(section["text"], max_extract_chars)
        extracts.append({"heading": section["heading"], "text": text,
                         "chars": len(text), "truncated": truncated})
    return extracts


def _public_record(rec: dict) -> dict:
    return {key: rec.get(key) for key in _PUBLIC_KEYS}


def _sort_by_score(records: list[dict], query_keywords: list[str] | None = None) -> list[dict]:
    """Sortuje malejąco po score; tie-break: liczba trafionych keywords, updated, path.

    Przy równym score większa liczba wspólnych keywords z query to silniejszy sygnał
    tematyczny (rozstrzyga przed świeżością). path jest finalnym, deterministycznym
    rozstrzygaczem - eliminuje niestabilną kolejność raportu przy identycznych kluczach.
    query_keywords=None -> tie-break po keywords nieaktywny (overlap=0 dla wszystkich).
    """
    qk = _norm_kw(query_keywords)

    def _overlap(rec: dict) -> int:
        return len(qk & _norm_kw(rec.get("keywords")))

    return sorted(records, key=lambda r: (r["score"], _overlap(r), r.get("updated") or "", r.get("path") or ""), reverse=True)


def _now_iso() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def build_context_pack(intent: str, root: str = ".", *, name: str = "", project: str = "",
                       keywords=None, angle: str = "", include_history: bool = False,
                       history_angle: str = "", max_items=None, days=None, limit=None,
                       today_iso: str | None = None) -> dict:
    """Buduje context pack dla intencji history/resume/handoff. Read-side authority."""
    if today_iso is None:
        today_iso = _now_iso()
    keywords = keywords or []
    budget = dict(BUDGETS[intent])
    # --limit (0 = bez limitu) zawęża listę kandydatów resume; budżet pozostaje twardym sufitem.
    if intent == "resume" and limit:
        budget["max_handoffs"] = min(budget["max_handoffs"], limit)
    query = {"name": name, "project": project, "keywords": keywords, "angle": angle, "days": days}
    records, skipped = load_records(root)

    pack = {
        "intent": intent,
        "query": query,
        "primary": None,
        "related": [],
        "items": [],
        "stats": {"matched": 0, "included": 0, "omitted": 0},
        "budget": budget,
        "presentation": {},
        "warnings": [],
    }

    if intent == "history":
        pack = _pack_history(pack, records, query, budget, max_items, today_iso)
    elif intent == "resume":
        pack = _pack_resume(pack, records, query, budget, include_history, history_angle, today_iso)
    elif intent == "handoff":
        pack = _pack_handoff(pack, records, query, budget, today_iso)
    else:
        raise ValueError(f"unknown intent: {intent}")

    _apply_skipped(pack, skipped)
    return pack


def _apply_skipped(pack: dict, skipped: dict) -> None:
    """Dokłada do packa fakty o pominiętych plikach (fail loud, nie ciche ucięcie)."""
    pack["stats"]["unreadable"] = len(skipped["unreadable"])
    pack["stats"]["incomplete_frontmatter"] = len(skipped["incomplete"])
    if skipped["unreadable"]:
        pack["warnings"].append("unreadable_files")
    if skipped["incomplete"]:
        pack["warnings"].append("incomplete_frontmatter")


def _score_all(records: list[dict], query: dict, today_iso: str) -> None:
    sub = {"name": query.get("name", ""), "project": query.get("project", ""),
           "keywords": query.get("keywords", [])}
    for rec in records:
        rec["score"] = score_record(rec, sub, today_iso)


def _pack_history(pack, records, query, budget, max_items, today_iso) -> dict:
    candidates = [r for r in records if _in_scope(r, query["project"], query["days"], today_iso)]
    matched = len(candidates)
    _score_all(candidates, query, today_iso)

    # Bramka trafności: gdy podano keywords, do items wchodzą tylko rekordy z niezerowym
    # (znormalizowanym) pokryciem keywords. Reszta w scope ma jedynie podłogę recency i jest
    # szumem tematycznym -> liczona w below_threshold, nie pokazywana jako traf.
    qk = _norm_kw(query.get("keywords"))
    relevant = [r for r in candidates if _norm_kw(r.get("keywords")) & qk] if qk else candidates
    below_threshold = matched - len(relevant)
    ordered = _sort_by_score(relevant, query.get("keywords"))

    cap_items = budget["max_items"]
    if max_items is not None:
        cap_items = min(cap_items, max_items)
    top = ordered[:cap_items]

    for rec in top:
        rec["extracts"] = _build_extracts(rec, EXTRACT_MAP.get(rec["type"], []),
                                          budget["max_extracts_per_item"], budget["max_extract_chars"])

    kept, used_chars = [], 0
    for rec in top:
        chars = sum(e["chars"] for e in rec["extracts"])
        if kept and used_chars + chars > budget["max_total_chars"]:
            break
        kept.append(rec)
        used_chars += chars

    keyword_index: dict[str, list[str]] = {}
    for rec in kept:
        for kw in dict.fromkeys(rec["keywords"]):
            keyword_index.setdefault(kw, []).append(rec["path"])

    pack["items"] = [_public_record(r) for r in kept]
    pack["stats"] = {"matched": matched, "relevant": len(relevant), "included": len(kept),
                     "omitted": len(relevant) - len(kept), "below_threshold": below_threshold}
    pack["budget"]["used_chars"] = used_chars
    pack["signals"] = {"keyword_index": keyword_index}
    pack["presentation"] = {
        "audience": "human",
        "output_contract": "compact_report",
        "group_by": "theme_then_date",
        "angle": query["angle"],
        "requires": ["dated_entries", "recurrence_callout", "already_done_callout", "references_path_heading"],
        "skeleton": ["title_range_stats", "themed_groups", "conclusions", "next_steps"],
        "max_followup_questions": 2,
    }
    if matched == 0:
        pack["warnings"].append("no_candidates")
    elif qk and not relevant:
        pack["warnings"].append("no_relevant")
    return pack


def _resume_tasks(records: list[dict], name: str) -> dict | None:
    """Stan zadań najświeższego dziennika schema 2 sesji `name` (wznowienie bez natywnej listy
    zadań musi znać postęp). Brak dziennika albo dziennik dawny -> None."""
    journals = [r for r in records if r["type"] == "execute" and r["name"] == name and r.get("_tasks")]
    if not journals:
        return None
    latest = max(journals, key=lambda r: (r.get("updated") or "", r["path"]))
    return {"execute": latest["path"], **latest["_tasks"]}


def _pack_resume(pack, records, query, budget, include_history, history_angle, today_iso) -> dict:
    handoffs = [r for r in records if r["type"] == "handoff"
                and _in_scope(r, query["project"], None, today_iso)]
    for rec in handoffs:
        rec["score"] = _recency_component(rec, today_iso)
    handoffs.sort(key=lambda r: r.get("updated") or "", reverse=True)

    name = query["name"]
    used_chars = 0
    pack["tasks"] = None
    if not name:
        related = handoffs[:budget["max_handoffs"]]
        for rec in related:
            rec["extracts"] = []
        pack["related"] = [_public_record(r) for r in related]
        pack["stats"] = {"matched": len(handoffs), "included": len(related),
                         "omitted": len(handoffs) - len(related)}
    else:
        matches = [r for r in handoffs if r["name"] == name]
        primary = matches[0] if matches else None
        if primary is not None:
            primary["extracts"] = _build_extracts(primary, RESUME_EXTRACT, len(RESUME_EXTRACT),
                                                  budget["max_extract_chars"])
            used_chars = sum(e["chars"] for e in primary["extracts"])
            pack["primary"] = _public_record(primary)
        if include_history:
            others = [r for r in records if r["path"] != (primary["path"] if primary else None)
                      and _in_scope(r, query["project"], None, today_iso)]
            hist_query = {"name": name, "project": query["project"], "keywords": query["keywords"]}
            for rec in others:
                rec["score"] = score_record(rec, hist_query, today_iso)
                rec["extracts"] = []
            related = _sort_by_score(others, hist_query.get("keywords"))[:budget["max_related_items"]]
            pack["related"] = [_public_record(r) for r in related]
        pack["stats"] = {"matched": len(handoffs), "included": 1 if primary else 0,
                         "omitted": 0}
        pack["tasks"] = _resume_tasks(records, name)
        if primary is None:
            pack["warnings"].append("not_found")

    pack["budget"]["used_chars"] = used_chars
    pack["presentation"] = {
        "audience": "agent",
        "output_contract": "continuation_context",
        "include_history": include_history,
        "history_angle": history_angle,
        "requires": ["pick_one_of_recent", "summarize_goal_progress_nextsteps", "continue_from_next_steps"],
    }
    if not handoffs and not name:
        pack["warnings"].append("no_candidates")
    return pack


def _pack_handoff(pack, records, query, budget, today_iso) -> dict:
    candidates = [r for r in records if _in_scope(r, query["project"], query["days"], today_iso)]
    matched = len(candidates)
    _score_all(candidates, query, today_iso)
    ordered = _sort_by_score(candidates, query.get("keywords"))
    related = ordered[:budget["max_related_items"]]
    for rec in related:
        rec["extracts"] = []

    pack["related"] = [_public_record(r) for r in related]
    pack["stats"] = {"matched": matched, "included": len(related), "omitted": matched - len(related)}
    pack["budget"]["used_chars"] = 0
    pack["presentation"] = {
        "audience": "next_agent",
        "output_contract": "session_snapshot_context",
        "requires": ["reference_related_by_path", "do_not_copy_bodies", "redact_secrets"],
    }
    if matched == 0:
        pack["warnings"].append("no_candidates")
    return pack


# --- Full-text recall (BM25, grupowane po SESJI) -----------------------------
# To NIE jest semantic search embeddingowy: to deterministyczny full-text recall.
# Użytkowa "semantyczność" bierze się z indeksowania pełnej treści (plan, dziennik,
# decyzje, weryfikacja) plus trwałego Original Prompt. Most PL<->EN to Original
# Prompt, nie magia. Jednostką wyszukiwania jest SESJA (wszystkie rekordy o tym
# samym `name`: plan + execute + handoff), bo użytkownik szuka przejazdu, nie pliku.

BM25_K1 = 1.5
BM25_B = 0.75
MIN_TERM_LEN = 2

# Most rdzeniowy (fuzzy): polski i angielski odmieniają SUFIKSY, więc dyskryminujący
# jest PREFIKS (rdzeń). Ekspansja zapytania na tokeny korpusu dzielące wspólny prefiks
# rdzenia (skinowanie~skin, ganta~gantt, licencja~license). Trzy bezpieczniki precyzji:
# (1) tylko tokeny >= FUZZY_MIN_TOKEN, (2) wspólny prefiks >= FUZZY_MIN_PREFIX i pokrycie
# >= FUZZY_MIN_SIM dłuższego tokenu, (3) kara FUZZY_PENALTY * podobieństwo - dokładny rdzeń
# zawsze bije rdzeniowy. matched_terms pokazuje most jawnie (`zapytanie~korpus`).
FUZZY_MIN_TOKEN = 4
FUZZY_MIN_PREFIX = 4
FUZZY_MIN_SIM = 0.5
FUZZY_PENALTY = 0.6

# Boost pól przy budowie ważonej reprezentacji termów sesji.
_FIELD_BOOST = {"keywords": 3, "name": 3, "title": 3, "original_prompt": 3, "body": 1}

# Krótka stoplista PL+EN (najczęstsze słowa funkcyjne). Reszta szumu tłumiona przez IDF.
_STOPWORDS = {
    "the", "and", "for", "are", "was", "this", "that", "with", "from", "has",
    "you", "your", "not", "but", "they", "our", "its",
    "na", "do", "to", "ze", "że", "sie", "się", "nie", "po", "za", "od", "jak",
    "co", "czy", "oraz", "lub", "dla", "przez", "jest", "sa", "są", "ten", "ta",
    "te", "tym", "tego", "albo", "bez", "lub",
}

# Nagłówek sekcji -> etykieta pola (do matched_fields).
_SECTION_FIELD = {
    "summary": "summary",
    "key changes": "key_changes",
    "original prompt": "original_prompt",
    "decisions and deviations": "decisions",
    "steps": "steps",
    "final result": "final",
    "verification": "verification",
    "goal": "goal",
    "next steps": "next_steps",
    "what didn't work": "red_lights",
    "what worked": "what_worked",
}

# Sloty streszczenia sesji (planned/decided/executed/verified/red_lights) -> nagłówek źródłowy.
_SLOT_SOURCES = (
    ("planned", "Summary"),
    ("decided", "Decisions And Deviations"),
    ("executed", "Final Result"),
    ("verified", "Verification"),
    ("red_lights", "What Didn't Work"),
)

_WORD_RE = re.compile(r"[^\W_]+", re.UNICODE)
# Granica camelCase: mała litera/cyfra, po której następuje wielka (też polska).
_CAMEL_RE = re.compile(r"(?<=[a-z0-9ąćęłńóśźż])(?=[A-ZĄĆĘŁŃÓŚŹŻ])")


def _terms(text) -> list[str]:
    """Tokenizacja do FTS: runy alfanumeryczne (Unicode), rozbicie camelCase, lower,
    stem liczby mnogiej, odsiew stoplisty i tokenów < MIN_TERM_LEN. Zwraca listę (z powtórzeniami).
    `welcome-page -> [welcome, page]`, `frWelcomePage -> [fr, welcome, page]`.
    """
    out: list[str] = []
    for run in _WORD_RE.findall(text or ""):
        for piece in _CAMEL_RE.sub(" ", run).split():
            t = _stem_kw(piece.lower())
            if len(t) >= MIN_TERM_LEN and t not in _STOPWORDS:
                out.append(t)
    return out


def _field_for_heading(heading: str) -> str:
    return _SECTION_FIELD.get((heading or "").strip().lower(), "body")


def _group_sessions(records: list[dict]) -> dict:
    """Grupuje rekordy po `name` (semantyczna nazwa sesji); fallback po ścieżce."""
    sessions: dict = {}
    for rec in records:
        key = rec.get("name") or rec.get("path")
        sessions.setdefault(key, []).append(rec)
    return sessions


def _session_terms(recs: list[dict]) -> tuple[Counter, dict]:
    """Ważona reprezentacja termów całej sesji + mapa term->zbiór pól, w których wystąpił."""
    tf: Counter = Counter()
    term_fields: dict = {}

    def add(text: str, boost: int, field: str) -> None:
        for t in _terms(text):
            tf[t] += boost
            term_fields.setdefault(t, set()).add(field)

    for rec in recs:
        add(" ".join(rec.get("keywords") or []), _FIELD_BOOST["keywords"], "keywords")
        add(rec.get("name", ""), _FIELD_BOOST["name"], "name")
        add(rec.get("title", ""), _FIELD_BOOST["title"], "title")
        # Indeksujemy TREŚĆ sekcji, nie tekst nagłówków: nagłówki to boilerplate szablonu
        # (Summary/Steps/Original Prompt...) identyczny dla wszystkich dokumentów - jego słowa
        # zafałszowałyby matched_terms/matched_fields (np. słowo "prompt" z nagłówka). Nagłówek
        # służy tylko do KLASYFIKACJI pola, do którego trafia treść.
        for sec in rec.get("_sections_full", []):
            if sec.get("is_placeholder"):
                continue
            field = _field_for_heading(sec.get("heading", ""))
            boost = _FIELD_BOOST["original_prompt"] if field == "original_prompt" else _FIELD_BOOST["body"]
            add(sec.get("text", ""), boost, field)
    return tf, term_fields


def _bm25_term(term: str, tf: Counter, dl: int, idf: dict, avgdl: float) -> float:
    """Wkład jednego termu do Okapi BM25 (k1, b) dla dokumentu-sesji."""
    f = tf.get(term, 0)
    if not f or dl <= 0 or avgdl <= 0:
        return 0.0
    denom = f + BM25_K1 * (1.0 - BM25_B + BM25_B * dl / avgdl)
    return idf.get(term, 0.0) * (f * (BM25_K1 + 1.0)) / denom


def _bm25_score_fuzzy(expansions: dict, tf: Counter, dl: int, idf: dict, avgdl: float) -> tuple[float, dict]:
    """BM25 z mostem rdzeniowym: dla każdego ORYGINALNEGO termu zapytania bierze najlepsze
    trafienie (dokładne albo rdzeniowe), bez podwójnego liczenia. `expansions` to
    {term_zapytania: {token_korpusu: podobieństwo}} (dokładny token ma podobieństwo 1.0).
    Zwraca (score, matched), gdzie matched: term_zapytania -> (token, czy_dokładny).
    """
    score = 0.0
    matched: dict = {}
    for qt, candidates in expansions.items():
        best = 0.0
        best_token = None
        best_exact = False
        for token, sim in candidates.items():
            base = _bm25_term(token, tf, dl, idf, avgdl)
            if not base:
                continue
            weight = 1.0 if token == qt else FUZZY_PENALTY * sim
            contrib = weight * base
            if contrib > best:
                best, best_token, best_exact = contrib, token, token == qt
        if best > 0:
            score += best
            matched[qt] = (best_token, best_exact)
    return score, matched


def _session_updated(recs: list[dict]) -> str:
    return max((r.get("updated") or "" for r in recs), default="")


def _session_title(recs: list[dict]) -> str:
    for typ in ("plan", "handoff", "execute"):
        for r in recs:
            if r.get("type") == typ and r.get("title"):
                return r["title"]
    for r in recs:
        if r.get("title"):
            return r["title"]
    return (recs[0].get("name", "") if recs else "")


def _summary_slots(recs: list[dict]) -> dict:
    """Deterministyczne sloty streszczenia sesji z konkretnych sekcji (retrieval, nie synteza)."""
    slots: dict = {}
    for slot, heading in _SLOT_SOURCES:
        text = ""
        for r in recs:
            sec = get_section(r.get("_sections_full", []), heading)
            if sec and not sec["is_placeholder"]:
                text = sec["text"]
                break
        slots[slot] = _truncate(" ".join(text.split()), 400)[0] if text else ""
    if not slots.get("red_lights"):
        for r in recs:
            sec = get_section(r.get("_sections_full", []), "Next Steps")
            if sec and not sec["is_placeholder"]:
                slots["red_lights"] = _truncate(" ".join(sec["text"].split()), 400)[0]
                break
    return slots


def _session_snippets(recs: list[dict], match_tokens: set, limit: int = 3) -> list[dict]:
    """Sekcje sesji z największą liczbą realnie dopasowanych tokenów (plik + nagłówek)."""
    cand: list[tuple] = []
    for r in recs:
        for sec in r.get("_sections_full", []):
            if sec.get("is_placeholder"):
                continue
            text = sec.get("text", "")
            hits = sum(1 for t in _terms(text) if t in match_tokens)
            if hits:
                cand.append((hits, r.get("type", ""), sec.get("heading", ""), text))
    cand.sort(key=lambda x: x[0], reverse=True)
    out: list[dict] = []
    for hits, typ, heading, text in cand[:limit]:
        out.append({"type": typ, "heading": heading, "hits": hits,
                    "text": _truncate(" ".join(text.split()), 240)[0]})
    return out


def _session_result(name: str, recs: list[dict], score: float, matched: dict,
                    tf: Counter, term_fields: dict) -> dict:
    # matched: term_zapytania -> (token_korpusu, czy_dokładny). Most rdzeniowy pokazujemy
    # jawnie jako `zapytanie~token`, żeby nigdy nie udawać dopasowania dokładnego.
    match_tokens = {tok for tok, _ in matched.values()}
    matched_terms = sorted(tok if exact else f"{qt}~{tok}" for qt, (tok, exact) in matched.items())
    matched_fields = sorted({f for tok in match_tokens for f in term_fields.get(tok, set())})
    artifacts = [{"type": r.get("type", ""), "path": r["path"], "status": r.get("status", "")}
                 for r in sorted(recs, key=lambda r: (r.get("type", ""), r["path"]))]
    project = next((r.get("project") for r in recs if r.get("project")), "")
    return {
        "session": name,
        "title": _session_title(recs),
        "project": project,
        "updated": _session_updated(recs),
        "score": round(score, 4),
        "coverage": len(matched),
        "matched_terms": matched_terms,
        "matched_fields": matched_fields,
        "artifacts": artifacts,
        "summary_slots": _summary_slots(recs),
        "snippets": _session_snippets(recs, match_tokens),
    }


def _apply_skipped_search(result: dict, skipped: dict) -> None:
    result["stats"]["unreadable"] = len(skipped["unreadable"])
    result["stats"]["incomplete_frontmatter"] = len(skipped["incomplete"])
    if skipped["unreadable"]:
        result["warnings"].append("unreadable_files")
    if skipped["incomplete"]:
        result["warnings"].append("incomplete_frontmatter")


def _common_prefix_len(a: str, b: str) -> int:
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return i


def _expand_term(qt: str, vocab: list[str]) -> dict:
    """Most rdzeniowy: tokeny korpusu dzielące z `qt` prefiks rdzenia. {token: podobieństwo},
    token dokładny ma podobieństwo 1.0. Tokeny < FUZZY_MIN_TOKEN nie są rozszerzane (anti-szum)."""
    out = {qt: 1.0}
    if len(qt) < FUZZY_MIN_TOKEN:
        return out
    for v in vocab:
        if v == qt:
            continue
        p = _common_prefix_len(qt, v)
        if p < FUZZY_MIN_PREFIX:
            continue
        sim = p / max(len(qt), len(v))
        if sim >= FUZZY_MIN_SIM:
            out[v] = max(out.get(v, 0.0), sim)
    return out


def search_corpus(root, query: str, *, limit: int = 10, project: str = "",
                  fuzzy: bool = True, today_iso: str | None = None) -> dict:
    """Full-text recall (BM25) nad korpusem, grupowany po sesji. Read-side authority.

    Zwraca history-result per sesja: session/title/score/matched_terms/matched_fields/
    artifacts/summary_slots/snippets. Wolny tekst na wejściu, ZERO wymaganego protokołu.
    Deterministyczny, indeks budowany per-zapytanie w pamięci. `fuzzy` włącza most rdzeniowy
    (prefiks) dla fleksji PL/EN; przy `fuzzy=False` liczy się tylko dopasowanie dokładne.
    """
    if today_iso is None:
        today_iso = _now_iso()
    records, skipped = load_records(root)
    in_scope = [r for r in records if _in_scope(r, project, None, today_iso)]
    query_terms = _terms(query)
    sessions = _group_sessions(in_scope)
    result = {
        "query": query,
        "query_terms": sorted(set(query_terms)),
        "mode": "bm25_fulltext",
        "fuzzy": fuzzy,
        "results": [],
        "stats": {"files_scanned": len(records), "files_in_scope": len(in_scope),
                  "sessions": len(sessions), "returned": 0},
        "warnings": [],
    }
    if not query_terms:
        result["warnings"].append("empty_query")
        _apply_skipped_search(result, skipped)
        return result

    built = []
    df: Counter = Counter()
    total_len = 0
    for key, recs in sessions.items():
        tf, term_fields = _session_terms(recs)
        dl = sum(tf.values())
        built.append((key, recs, tf, term_fields, dl))
        total_len += dl
        for t in tf:
            df[t] += 1
    n = len(built)
    avgdl = (total_len / n) if n else 0.0
    idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}

    # Ekspansja rdzeniowa liczona raz na całe zapytanie (słownik = tokeny korpusu).
    vocab = [t for t in df if len(t) >= FUZZY_MIN_TOKEN] if fuzzy else []
    expansions = {qt: (_expand_term(qt, vocab) if fuzzy else {qt: 1.0}) for qt in set(query_terms)}

    scored = []
    for key, recs, tf, term_fields, dl in built:
        s, matched = _bm25_score_fuzzy(expansions, tf, dl, idf, avgdl)
        if s > 0:
            scored.append((s, key, recs, tf, term_fields, matched))
    # Ranking: POKRYCIE nadrzędne (ile różnych słów zapytania trafiło), bo sesja z dwoma
    # słowami ma bić sesję z jednym; BM25 (rzadkość+częstość) rozstrzyga w obrębie pokrycia,
    # potem świeżość i deterministyczny klucz.
    scored.sort(key=lambda x: (len(x[5]), x[0], _session_updated(x[2]), x[1]), reverse=True)

    top = scored if limit <= 0 else scored[:limit]
    result["results"] = [_session_result(key, recs, s, matched, tf, term_fields)
                         for s, key, recs, tf, term_fields, matched in top]
    result["stats"]["returned"] = len(result["results"])
    if not scored:
        result["warnings"].append("no_matches")
    _apply_skipped_search(result, skipped)
    return result
