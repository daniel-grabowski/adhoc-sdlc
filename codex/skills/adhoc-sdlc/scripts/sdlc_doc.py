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
import re
import time
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


def _jaccard(a: list[str], b: list[str]) -> float:
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
        components.append((WEIGHT_KEYWORD, _jaccard(q_keywords, rec.get("keywords") or [])))
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
        return {"path": str(path), "meta": {}, "sections": [], "warnings": ["invalid_json"], "touched_files": []}

    meta = {k: data.get(k, "") for k in _JSON_META_KEYS}
    meta["keywords"] = data.get("keywords", []) or []
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
    sections = [
        {"heading": "Steps", "level": 2, "text": steps_text, "is_placeholder": steps_text == ""},
        {"heading": "Decisions And Deviations", "level": 2, "text": dec_text, "is_placeholder": dec_text == ""},
        {"heading": "Verification", "level": 2, "text": ver_text, "is_placeholder": ver_text == ""},
        {"heading": "Final Result", "level": 2, "text": final, "is_placeholder": final == ""},
    ]

    seen, touched = set(), []
    for e in entries:
        for f in (e.get("files") or []):
            p = (f.get("path", "") if isinstance(f, dict) else str(f)).strip()
            if p and p not in seen:
                seen.add(p)
                touched.append({"path": p, "change": (f.get("change", "") if isinstance(f, dict) else "")})

    return {"path": str(path), "meta": meta, "sections": sections, "warnings": [], "touched_files": touched}


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
            "keywords": meta.get("keywords", []) or [],
            "created": meta.get("created", ""),
            "updated": meta.get("updated", meta.get("created", "")) or "",
            "status": meta.get("status", ""),
            "score": 0.0,
            "sections": [{"heading": s["heading"], "is_placeholder": s["is_placeholder"]}
                         for s in doc["sections"] if s["heading"] != ""],
            "extracts": [],
            "touched_files": doc.get("touched_files", []),
            "_sections_full": doc["sections"],
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


def _sort_by_score(records: list[dict]) -> list[dict]:
    return sorted(records, key=lambda r: (r["score"], r.get("updated") or ""), reverse=True)


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
    ordered = _sort_by_score(candidates)

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
        for kw in rec["keywords"]:
            keyword_index.setdefault(kw, []).append(rec["path"])

    pack["items"] = [_public_record(r) for r in kept]
    pack["stats"] = {"matched": matched, "included": len(kept), "omitted": matched - len(kept)}
    pack["budget"]["used_chars"] = used_chars
    pack["signals"] = {"keyword_index": keyword_index}
    pack["presentation"] = {
        "audience": "human",
        "output_contract": "compact_report",
        "group_by": "theme_then_date",
        "angle": query["angle"],
        "requires": ["dated_entries", "recurrence_callout", "already_done_callout", "references_path_heading"],
        "skeleton": ["title_range_stats", "themed_groups", "wnioski", "co_dalej"],
        "max_followup_questions": 2,
    }
    if matched == 0:
        pack["warnings"].append("no_candidates")
    return pack


def _pack_resume(pack, records, query, budget, include_history, history_angle, today_iso) -> dict:
    handoffs = [r for r in records if r["type"] == "handoff"
                and _in_scope(r, query["project"], None, today_iso)]
    for rec in handoffs:
        rec["score"] = _recency_component(rec, today_iso)
    handoffs.sort(key=lambda r: r.get("updated") or "", reverse=True)

    name = query["name"]
    used_chars = 0
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
            related = _sort_by_score(others)[:budget["max_related_items"]]
            pack["related"] = [_public_record(r) for r in related]
        pack["stats"] = {"matched": len(handoffs), "included": 1 if primary else 0,
                         "omitted": 0}
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
    ordered = _sort_by_score(candidates)
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
