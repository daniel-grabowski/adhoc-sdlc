#!/usr/bin/env python3
"""Manage lightweight adhoc-sdlc plan, execution, and handoff files in the current project.

Kanon protokołu: helper jest twardym strażnikiem kontraktu. Każde wywołanie z błędnym
wejściem -> odmowa (ContractError -> exit 2 + komunikat ERROR/EXPECTED/EXAMPLE), zero
efektów ubocznych. Pliki adhoc-sdlc/ tworzy WYŁĄCZNIE ten helper (jedyne źródło prawdy
dla nazw i frontmatter YAML).
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
import unicodedata

import sdlc_doc


# Domyślny root = bieżący katalog roboczy (resolve do cwd przy uruchomieniu).
DEFAULT_ROOT = Path(".")

VALID_STATUS = ("in-progress", "done", "abandoned")
VALID_CHANGES = ("edit", "add", "delete", "rename")
VALID_KINDS = ("handoff", "plan", "execute", "all")
VALID_FORMATS = ("json", "tsv")
VALID_INTENTS = ("history", "resume", "handoff")
KIND_PREFIXES = ("plan", "execute", "handoff")

# Token projektu: pojedyncze słowo (nazwa repo/obszaru).
PROJECT_RE = re.compile(r"^[a-z0-9._-]+$")
# Wzorzec nazwy pliku dziennika: <kind>-<data[-czas]>-<name>.md
FILENAME_RE = re.compile(r"^(plan|execute|handoff)-(\d{4}-\d{2}-\d{2}(?:-\d{6})?)-(.+)\.(?:md|json)$")


class ContractError(Exception):
    """Naruszenie kontraktu wejścia. Mapuje na exit 2 + komunikat ERROR/EXPECTED/EXAMPLE."""

    def __init__(self, error: str, expected: str, example: str) -> None:
        super().__init__(error)
        self.error = error
        self.expected = expected
        self.example = example

    def emit(self) -> None:
        print(f"ERROR: {self.error}", file=sys.stderr)
        print(f"EXPECTED: {self.expected}", file=sys.stderr)
        print(f"EXAMPLE: {self.example}", file=sys.stderr)


def semantic_name(raw: str) -> str:
    normalized = unicodedata.normalize("NFKD", raw)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_text.lower()
    name = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    name = re.sub(r"-{2,}", "-", name)
    return name


def require_name(raw: str | None, mode: str) -> str:
    if not raw or not raw.strip():
        raise ContractError(
            "brak wymaganego argumentu --name",
            "niepusty opis nazwy sesji/zadania",
            f'{mode} --name "rf001 state duration" --title "RF-001 czas trwania"',
        )
    name = semantic_name(raw)
    if not name:
        raise ContractError(
            f"--name normalizuje się do pustej wartości: {raw!r}",
            "nazwa musi zawierać znaki alfanumeryczne (a-z, 0-9)",
            f'{mode} --name "rf001 state duration" --title "RF-001 czas trwania"',
        )
    return name


def require_title(raw: str | None, mode: str) -> str:
    if not raw or not raw.strip():
        raise ContractError(
            "brak wymaganego argumentu --title",
            "niepusty, ludzki tytuł",
            f'{mode} --name "rf001" --title "RF-001 czas trwania statusu"',
        )
    return raw.strip()


def validate_status(raw: str | None, mode: str) -> str:
    if raw is None:
        return "in-progress"
    if raw not in VALID_STATUS:
        raise ContractError(
            f"niedozwolony --status: {raw!r}",
            f"jedna z wartości: {', '.join(VALID_STATUS)}",
            f"{mode} --name x --title T --status done",
        )
    return raw


def parse_keywords(raw: str | None, mode: str) -> list[str]:
    if raw is None:
        return []
    tokens: list[str] = []
    for chunk in raw.split(","):
        token = semantic_name(chunk)
        if not token:
            raise ContractError(
                f"pusty/niepoprawny token w --keywords: {chunk!r}",
                "lista tokenów [a-z0-9-] rozdzielonych przecinkami, bez pustych",
                f"{mode} --name x --title T --keywords rest,rf001,build",
            )
        if token not in tokens:  # dedup z zachowaniem kolejności pierwszego wystąpienia
            tokens.append(token)
    return tokens


def validate_project(raw: str | None, mode: str) -> str:
    if raw is None:
        return ""
    value = raw.strip()
    if value == "" or not PROJECT_RE.match(value):
        raise ContractError(
            f"niepoprawny --project: {raw!r}",
            "pojedynczy token [a-z0-9._-] (bez spacji)",
            f"{mode} --name x --title T --project dflex-rest",
        )
    return value


def validate_kind(raw: str) -> str:
    if raw not in VALID_KINDS:
        raise ContractError(
            f"niedozwolony --kind: {raw!r}",
            f"jedna z wartości: {', '.join(VALID_KINDS)}",
            "list --kind handoff --limit 4",
        )
    return raw


def validate_format(raw: str) -> str:
    if raw not in VALID_FORMATS:
        raise ContractError(
            f"niedozwolony --format: {raw!r}",
            f"jedna z wartości: {', '.join(VALID_FORMATS)}",
            "list --kind all --limit 0 --format json",
        )
    return raw


def validate_limit(raw: int) -> int:
    if raw < 0:
        raise ContractError(
            f"niedozwolony --limit: {raw}",
            "liczba całkowita >= 0 (0 = bez limitu)",
            "list --kind handoff --limit 4",
        )
    return raw


def target_dir(root: Path) -> Path:
    return root / "adhoc-sdlc"


def now() -> str:
    return dt.datetime.now().astimezone().isoformat(timespec="seconds")


def today() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d")


def stamp() -> str:
    return dt.datetime.now().strftime("%Y-%m-%d-%H%M%S")


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def find_plans(path: Path, name: str) -> list[Path]:
    return sorted(path.glob(f"plan-*-{name}.md"))


def find_executes(path: Path, name: str) -> list[Path]:
    # Nowe dzienniki to JSON; stare (markdown) nadal wykrywamy dla kolizji i kontynuacji.
    return sorted(path.glob(f"execute-*-{name}.md")) + sorted(path.glob(f"execute-*-{name}.json"))


def write_exclusive(path: Path, content: str) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
    except Exception:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


# --- Frontmatter: jeden writer i jeden parser dla wszystkich trybów -----------

def _esc(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _unesc(value: str) -> str:
    return value.replace('\\"', '"').replace("\\\\", "\\")


def build_frontmatter(meta: dict) -> str:
    keywords = meta.get("keywords") or []
    lines = [
        "---",
        f"type: {meta['type']}",
        f"name: {meta['name']}",
        f'title: "{_esc(meta["title"])}"',
        f'project: "{_esc(meta.get("project", ""))}"',
        "keywords: [" + ", ".join(keywords) + "]",
        f"created: {meta['created']}",
        f"updated: {meta['updated']}",
        f"status: {meta['status']}",
        "---",
        "",
    ]
    return "\n".join(lines) + "\n"


def read_frontmatter(path: Path) -> dict:
    """Zwraca dict metadanych z frontmatter albo {} gdy go brak."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end == -1:
        return {}
    block = text[4:end]
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


def update_frontmatter_field(text: str, key: str, value: str) -> str:
    """Aktualizuje pojedyncze pole frontmatter (gołą wartość) w treści pliku."""
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---", 4)
    if end == -1:
        return text
    head = text[:end]
    tail = text[end:]
    pattern = re.compile(rf"^({re.escape(key)}:).*$", re.MULTILINE)
    if pattern.search(head):
        head = pattern.sub(rf"\1 {value}", head, count=1)
    return head + tail


# --- Szablony body ------------------------------------------------------------

def plan_body() -> str:
    return """## Summary

TODO

## Key Changes

TODO

## Test Plan

TODO

## Assumptions

TODO
"""


def execute_body(plan_path: Path, created_at: str, entry: str | None) -> str:
    first_entry = entry or "Execution journal created."
    return f"""Plan: `{plan_path}`

## Steps

- {created_at}: {first_entry}

## Decisions And Deviations

None yet.

## Verification

Not run yet.

## Final Result

Pending.
"""


def handoff_body() -> str:
    return """## Goal

TODO

## Current Progress

TODO

## What Worked

TODO

## What Didn't Work

TODO

## Next Steps

TODO

## Suggested Skills

TODO
"""


# --- Tryby --------------------------------------------------------------------

def append_step(path: Path, entry: str, status: str | None) -> None:
    text = path.read_text(encoding="utf-8")
    meta, body = sdlc_doc.split_frontmatter(text)
    new_body = sdlc_doc.append_to_section(body, "Steps", [f"- {now()}: {entry}", ""])
    if new_body is None:
        raise RuntimeError(f"cannot append step; missing 'Steps' section in {path}")
    head = text[: len(text) - len(body)]
    text = update_frontmatter_field(head + new_body, "updated", now())
    if status is not None:
        text = update_frontmatter_field(text, "status", status)
    path.write_text(text, encoding="utf-8", newline="\n")


# --- Dziennik wykonania jako JSON (przyrostowy, helper jest jedynym writerem) --

def parse_files(raw: str | None, change: str, mode: str) -> list[dict]:
    """Lista ścieżek z --files 'a,b,c' na rekordy {path, change}. Pusty -> []."""
    if not raw:
        return []
    if change not in VALID_CHANGES:
        raise ContractError(
            f"niedozwolony --change: {change!r}",
            f"jedna z wartości: {', '.join(VALID_CHANGES)}",
            f'{mode} --name x --title T --append "krok" --files a.pas,b.pas --change edit',
        )
    files = []
    for chunk in raw.split(","):
        path = chunk.strip()
        if not path:
            raise ContractError(
                f"pusta ścieżka w --files: {raw!r}",
                "lista ścieżek rozdzielonych przecinkami, bez pustych",
                f'{mode} --name x --title T --append "krok" --files Rest2.Types.pas,DTO.Reader.pas',
            )
        files.append({"path": path, "change": change})
    return files


def make_entry(note: str, files: list[dict], phase: str) -> dict:
    """Pojedynczy wpis przyrostowy dziennika: nota + opcjonalna faza i dotknięte pliki."""
    entry: dict = {"ts": now(), "note": note}
    if phase:
        entry["phase"] = phase
    if files:
        entry["files"] = files
    return entry


def build_execute_obj(meta: dict, plan_path: Path, first_entry: dict | None) -> dict:
    return {
        "type": "execute",
        "name": meta["name"],
        "title": meta["title"],
        "project": meta.get("project", ""),
        "keywords": meta.get("keywords", []),
        "created": meta["created"],
        "updated": meta["updated"],
        "status": meta["status"],
        "plan": str(plan_path),
        "entries": [first_entry] if first_entry else [],
        "decisions": [],
        "verification": [],
        "final_result": None,
    }


def dump_execute_json(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2) + "\n"


def save_execute_json(path: Path, obj: dict) -> None:
    """Zapis atomowy: temp + os.replace. Częściowy zapis (EIO na 9P) nie uszkadza oryginału."""
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(dump_execute_json(obj))
    os.replace(tmp, path)


def update_execute_json(path: Path, *, note: str | None, files: list[dict], phase: str,
                        decision: str | None, verification: str | None, command: str | None,
                        final: str | None, status: str | None) -> None:
    """Read-modify-write całego obiektu JSON. Każda obecna operacja dokłada się do dziennika."""
    obj = json.loads(path.read_text(encoding="utf-8"))
    changed = False
    if note:
        obj.setdefault("entries", []).append(make_entry(note, files, phase))
        changed = True
    if decision:
        obj.setdefault("decisions", []).append({"ts": now(), "text": decision})
        changed = True
    if verification:
        obj.setdefault("verification", []).append(
            {"ts": now(), "command": command or "", "outcome": verification})
        changed = True
    if final is not None:
        obj["final_result"] = final
        changed = True
    if status is not None:
        obj["status"] = status
        changed = True
    if changed:
        obj["updated"] = now()
        save_execute_json(path, obj)


def cmd_plan(args: argparse.Namespace) -> int:
    mode = "plan"
    name = require_name(args.name, mode)
    title = require_title(args.title, mode)
    status = validate_status(args.status, mode)
    keywords = parse_keywords(args.keywords, mode)
    project = validate_project(args.project, mode)

    root = Path(args.root).resolve()
    path = target_dir(root)
    ensure_dir(path)
    collisions = find_plans(path, name) + find_executes(path, name)
    if collisions:
        raise ContractError(
            f"semantic name już użyty: {name} ({len(collisions)} plik(ów))",
            "unikalna nazwa sesji/zadania (sprawdź istniejące plan-*/execute-*)",
            f'plan --name "{name}-v2" --title "..."',
        )
    created_at = now()
    date_value = args.date or today()
    plan_path = path / f"plan-{date_value}-{name}.md"
    meta = {"type": "plan", "name": name, "title": title, "project": project,
            "keywords": keywords, "created": created_at, "updated": created_at, "status": status}
    write_exclusive(plan_path, build_frontmatter(meta) + plan_body())
    print(f"semantic_name={name}")
    print(f"plan={plan_path}")
    return 0


def cmd_execute(args: argparse.Namespace) -> int:
    mode = "execute"
    name = require_name(args.name, mode)
    title = require_title(args.title, mode)
    status = validate_status(args.status, mode) if args.status is not None else None
    keywords = parse_keywords(args.keywords, mode)
    project = validate_project(args.project, mode)
    note = (args.note if getattr(args, "note", None) else args.append) or None
    phase = (args.phase or "").strip()
    files = parse_files(args.files, args.change or "edit", mode)
    if (files or phase) and not note:
        raise ContractError(
            "--files/--phase należą do wpisu i wymagają także --append/--note",
            "dodaj notę kroku, do której przypisane są pliki/faza",
            f'execute --name "{name}" --title "T" --append "krok" --files a.pas,b.pas --phase "setup"',
        )
    if args.command and not args.verification:
        raise ContractError(
            "--command należy do wyniku weryfikacji i wymaga także --verification",
            "podaj outcome weryfikacji, do którego przypisana jest komenda",
            f'execute --name "{name}" --title "T" --verification "zielone" --command "npm test"',
        )

    root = Path(args.root).resolve()
    path = target_dir(root)
    ensure_dir(path)
    plans = find_plans(path, name)
    if len(plans) != 1:
        raise ContractError(
            f"oczekiwano dokładnie jednego planu dla: {name}; znaleziono {len(plans)}",
            "najpierw utwórz plan (adhoc_sdlc.py plan ...) o tej samej nazwie",
            f'plan --name "{name}" --title "..."  # potem: execute --name "{name}" --title "..."',
        )
    executes = find_executes(path, name)
    if len(executes) > 1:
        raise ContractError(
            f"niejednoznaczne dzienniki wykonania dla: {name} ({len(executes)})",
            "dokładnie jeden execute-*-<name>.{json,md}",
            f"usuń nadmiarowe execute-*-{name}.* ręcznie",
        )
    if executes:
        execute_path = executes[0]
        if str(execute_path).endswith(".json"):
            update_execute_json(execute_path, note=note, files=files, phase=phase,
                                decision=args.decision, verification=args.verification,
                                command=args.command, final=args.final, status=status)
        else:
            # Stary dziennik markdown: kontynuujemy go starym torem (kompatybilność),
            # ale nowych pól strukturalnych nie da się w nim zapisać - fail loud.
            extras = [n for n, v in (("--files", files), ("--phase", phase),
                                     ("--decision", args.decision), ("--verification", args.verification),
                                     ("--final", args.final)) if v]
            if extras:
                raise ContractError(
                    f"stary dziennik markdown nie wspiera pól: {', '.join(extras)}",
                    'kontynuuj go przez samo --append "..." albo zakończ i utwórz nowy dziennik (JSON)',
                    f'execute --name "{name}" --title "T" --append "krok"',
                )
            if note:
                append_step(execute_path, note, status)
        print(f"semantic_name={name}")
        print(f"plan={plans[0]}")
        print(f"execute={execute_path}")
        return 0

    created_at = now()
    execute_path = path / f"execute-{args.date or today()}-{name}.json"
    meta = {"name": name, "title": title, "project": project, "keywords": keywords,
            "created": created_at, "updated": created_at, "status": status or "in-progress"}
    obj = build_execute_obj(meta, plans[0], make_entry(note, files, phase) if note else None)
    if args.decision:
        obj["decisions"].append({"ts": created_at, "text": args.decision})
    if args.verification:
        obj["verification"].append({"ts": created_at, "command": args.command or "", "outcome": args.verification})
    if args.final is not None:
        obj["final_result"] = args.final
    write_exclusive(execute_path, dump_execute_json(obj))
    print(f"semantic_name={name}")
    print(f"plan={plans[0]}")
    print(f"execute={execute_path}")
    return 0


def cmd_handoff(args: argparse.Namespace) -> int:
    mode = "handoff"
    name = require_name(args.name, mode)
    title = require_title(args.title, mode)
    status = validate_status(args.status, mode)
    keywords = parse_keywords(args.keywords, mode)
    project = validate_project(args.project, mode)

    root = Path(args.root).resolve()
    path = target_dir(root)
    ensure_dir(path)
    created_at = now()
    stamp_value = args.date or stamp()
    handoff_path = path / f"handoff-{stamp_value}-{name}.md"
    if handoff_path.exists():
        raise ContractError(
            f"plik handoff już istnieje: {handoff_path.name}",
            "kolizja stempla czasu jest praktycznie niemożliwa — ponów za sekundę",
            "handoff --name x --title T",
        )
    meta = {"type": "handoff", "name": name, "title": title, "project": project,
            "keywords": keywords, "created": created_at, "updated": created_at, "status": status}
    write_exclusive(handoff_path, build_frontmatter(meta) + handoff_body())
    print(f"semantic_name={name}")
    print(f"handoff={handoff_path}")
    return 0


def _heading_title(path: Path) -> str:
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    except OSError:
        pass
    return path.stem


def _record_for(path: Path) -> dict:
    fm = FILENAME_RE.match(path.name)
    if str(path).endswith(".json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        return {
            "path": str(path),
            "type": data.get("type") or (fm.group(1) if fm else "execute"),
            "name": data.get("name") or (fm.group(3) if fm else path.stem),
            "title": data.get("title", ""),
            "project": data.get("project", ""),
            "keywords": data.get("keywords", []) or [],
            "created": data.get("created", ""),
            "updated": data.get("updated", data.get("created", "")),
            "status": data.get("status", ""),
        }
    meta = read_frontmatter(path)
    if meta:
        rec = {
            "path": str(path),
            "type": meta.get("type", fm.group(1) if fm else ""),
            "name": meta.get("name", fm.group(3) if fm else path.stem),
            "title": meta.get("title", ""),
            "project": meta.get("project", ""),
            "keywords": meta.get("keywords", []),
            "created": meta.get("created", ""),
            "updated": meta.get("updated", meta.get("created", "")),
            "status": meta.get("status", ""),
        }
    else:
        # Fallback dla starszych plików bez frontmatter.
        try:
            mtime = dt.datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds")
        except OSError:
            mtime = ""
        rec = {
            "path": str(path),
            "type": fm.group(1) if fm else "",
            "name": fm.group(3) if fm else path.stem,
            "title": _heading_title(path),
            "project": "",
            "keywords": [],
            "created": mtime,
            "updated": mtime,
            "status": "",
        }
    return rec


def cmd_list(args: argparse.Namespace) -> int:
    kind = validate_kind(args.kind)
    fmt = validate_format(args.format)
    limit = validate_limit(args.limit)

    root = Path(args.root).resolve()
    path = target_dir(root)
    kinds = KIND_PREFIXES if kind == "all" else (kind,)
    files: list[Path] = []
    if path.is_dir():
        for prefix in kinds:
            files.extend(path.glob(f"{prefix}-*.md"))
            if prefix == "execute":
                files.extend(path.glob("execute-*.json"))

    records = [_record_for(p) for p in files]
    if args.project:
        project = validate_project(args.project, "list")
        records = [r for r in records if r.get("project") == project]
    records.sort(key=lambda r: (r.get("updated") or r.get("created") or ""), reverse=True)
    if limit > 0:
        records = records[:limit]

    if fmt == "json":
        print(json.dumps(records, ensure_ascii=False, indent=2))
    else:
        for r in records:
            kw = ",".join(r.get("keywords") or [])
            print("\t".join([r["path"], r.get("type", ""), r.get("updated", ""),
                             r.get("project", ""), kw, r.get("title", "")]))
    return 0


def validate_intent(raw: str | None) -> str:
    if raw not in VALID_INTENTS:
        raise ContractError(
            f"niedozwolony --intent: {raw!r}",
            f"jedna z wartości: {', '.join(VALID_INTENTS)}",
            'pack --intent history --angle "powtarzające się problemy" --keywords build,fpc',
        )
    return raw


def cmd_pack(args: argparse.Namespace) -> int:
    mode = "pack"
    intent = validate_intent(args.intent)
    fmt = validate_format(args.format)
    if fmt != "json":
        raise ContractError(
            f"niedozwolony --format dla pack: {fmt!r}",
            "pack zwraca wyłącznie json",
            "pack --intent resume --format json",
        )
    angle = (args.angle or "").strip()
    if angle and intent != "history":
        raise ContractError(
            f"--angle dozwolone tylko dla --intent history (otrzymano intent={intent})",
            "usuń --angle albo użyj --intent history",
            'pack --intent history --angle "..." --keywords a,b',
        )
    keywords = parse_keywords(args.keywords, mode)
    if intent == "history" and not angle and not keywords:
        raise ContractError(
            "intent=history wymaga kąta: podaj --angle i/lub --keywords",
            "agent ekstrahuje keywords z kąta i przekazuje --keywords (+ surowy --angle)",
            'pack --intent history --angle "problemy z buildem" --keywords build,fpc',
        )
    project = validate_project(args.project, mode)
    name = semantic_name(args.name) if args.name else ""
    for value, label in ((args.max_items, "--max-items"), (args.days, "--days"), (args.limit, "--limit")):
        if value is not None and value < 0:
            raise ContractError(
                f"niedozwolony {label}: {value}",
                "liczba całkowita >= 0",
                "pack --intent history --angle x --keywords a --max-items 5",
            )

    root = Path(args.root).resolve()
    pack = sdlc_doc.build_context_pack(
        intent, root=str(root), name=name, project=project, keywords=keywords, angle=angle,
        include_history=args.include_history, history_angle=(args.history_angle or ""),
        max_items=args.max_items, days=args.days, limit=args.limit, today_iso=now(),
    )
    print(json.dumps(pack, ensure_ascii=False, indent=2))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="create a confirmed plan file only")
    plan.add_argument("--root", default=str(DEFAULT_ROOT))
    plan.add_argument("--name")
    plan.add_argument("--title")
    plan.add_argument("--project")
    plan.add_argument("--keywords")
    plan.add_argument("--status")
    plan.add_argument("--date")
    plan.set_defaults(func=cmd_plan)

    execute = sub.add_parser("execute", help="create or append an execution journal (JSON)")
    execute.add_argument("--root", default=str(DEFAULT_ROOT))
    execute.add_argument("--name")
    execute.add_argument("--title")
    execute.add_argument("--project")
    execute.add_argument("--keywords")
    execute.add_argument("--status")
    execute.add_argument("--append", help="treść wpisu kroku (alias --note)")
    execute.add_argument("--note", help="treść wpisu kroku (alias --append)")
    execute.add_argument("--phase", help="opcjonalna etykieta zadania/fazy dla wpisu")
    execute.add_argument("--files", help="lista dotkniętych plików dla wpisu, np. a.pas,b.pas")
    execute.add_argument("--change", help=f"rodzaj zmiany dla --files: {', '.join(VALID_CHANGES)} (domyślnie edit)")
    execute.add_argument("--decision", help="dopisz decyzję/odstępstwo")
    execute.add_argument("--verification", help="dopisz wynik weryfikacji (outcome)")
    execute.add_argument("--command", help="komenda powiązana z --verification")
    execute.add_argument("--final", help="ustaw końcowy wynik (final_result)")
    execute.add_argument("--date")
    execute.set_defaults(func=cmd_execute)

    handoff = sub.add_parser("handoff", help="create a session handoff snapshot")
    handoff.add_argument("--root", default=str(DEFAULT_ROOT))
    handoff.add_argument("--name")
    handoff.add_argument("--title")
    handoff.add_argument("--project")
    handoff.add_argument("--keywords")
    handoff.add_argument("--status")
    handoff.add_argument("--date")
    handoff.set_defaults(func=cmd_handoff)

    listing = sub.add_parser("list", help="list journal files with metadata (json/tsv)")
    listing.add_argument("--root", default=str(DEFAULT_ROOT))
    listing.add_argument("--kind", default="all")
    listing.add_argument("--limit", type=int, default=0)
    listing.add_argument("--project")
    listing.add_argument("--format", default="json")
    listing.set_defaults(func=cmd_list)

    pack = sub.add_parser("pack", help="build a read-side context pack (json) for the agent")
    pack.add_argument("--root", default=str(DEFAULT_ROOT))
    pack.add_argument("--intent")
    pack.add_argument("--name")
    pack.add_argument("--project")
    pack.add_argument("--keywords")
    pack.add_argument("--angle")
    pack.add_argument("--include-history", action="store_true")
    pack.add_argument("--history-angle")
    pack.add_argument("--max-items", type=int)
    pack.add_argument("--days", type=int)
    pack.add_argument("--limit", type=int)
    pack.add_argument("--format", default="json")
    pack.set_defaults(func=cmd_pack)

    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except ContractError as exc:
        exc.emit()
        return 2
    except (OSError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
