#!/usr/bin/env python3
"""Validate a Jin Chan Chan forecast ledger (forecasts/ledger.json).

Read-only: this script never writes to the ledger. It checks the
schema defined in design/forecast-ledger-schema.md (schema_version 1.0):

  - forecast_id is unique and matches ^S[0-9]+-FC-[0-9]{2,}$
  - all required fields are present and non-empty
  - probability is a number in [0, 1]
  - information_cutoff <= created_at < resolution_deadline
  - every resolution references an existing forecast_id
  - at most one non-review resolution per forecast_id; later ones
    must be marked review=true with a review_reason
  - resolver is never the forecast author or agent
  - score is present exactly for hit/miss and equals the Brier score
    (p - actual_outcome)^2 within 0.0001
  - forecast status agrees with its latest resolution
  - the version chain is self-consistent: versions run 1..N with no
    gaps, supersedes/superseded_by agree, superseded_by points at an
    existing newer version, the forecasts entry equals the latest
    version content, and created_at is identical across versions
  - every evidence item carries a non-empty excerpt (a bare URL is
    not evidence); a verified item needs a source locator and a
    publication date, and an item without a source is unverified

With --git, the script also checks git history: every version-chain
record that appears in any committed copy of the ledger must still
appear unchanged in the current ledger. History may not be rewritten.
The comparison ignores superseded_by: that field is a forward pointer
that legitimately changes from null to N+1 when version N+1 is
appended. Every other field of a version record is immutable.

Usage:
  python3 scripts/validate_ledger.py [ledger.json] [--git] [--quiet]

Exit code is 0 when the ledger passes, 1 when any check fails,
2 for usage errors (missing file, unparsable JSON).
"""

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone

SCHEMA_VERSION = "1.0"
FORECAST_ID_RE = re.compile(r"^S[0-9]+-FC-[0-9]{2,}$")
BRIER_TOLERANCE = 0.0001

FORECAST_TYPES = {
    "active_action", "external_event", "reaction", "impact", "state",
}
FORECAST_STATUSES = {"open", "resolved", "void"}
VERIFICATION_RESULTS = {"verified", "unverified", "contradicted"}
RESOLUTION_STATUSES = {
    "hit", "miss", "not_yet_due", "indeterminate", "disputed",
}
DISPUTE_STATUSES = {"none", "open", "resolved"}

FORECAST_FIELDS = {
    "forecast_id", "proposition", "forecast_type", "type",
    "participants", "author", "agent", "created_at",
    "information_cutoff", "resolution_deadline", "probability",
    "resolution_criteria", "evidence_snapshot", "reasoning_summary",
    "assumptions", "counter_evidence", "model_version",
    "method_version", "rule_version", "world_state_version", "status",
}
VERSION_FIELDS = {
    "forecast_id", "version", "supersedes", "superseded_by",
    "created_at", "change", "content",
}
RESOLUTION_FIELDS = {
    "forecast_id", "actual_outcome", "resolved_at", "outcome_evidence",
    "resolution_status", "resolver", "dispute_status", "score",
    "review", "review_reason", "forecast_version",
}
EVIDENCE_FIELDS = {
    "source_url", "publisher", "published_at", "retrieved_at",
    "excerpt", "verification_result",
}
TOP_LEVEL_FIELDS = {
    "schema_version", "meta", "forecasts", "resolutions", "versions",
}


def parse_time(value):
    """Parse an ISO 8601 date or datetime into an aware datetime.

    A trailing Z means UTC. A bare date means midnight UTC on that
    date. A naive datetime is read as UTC. Returns None when the
    value is not a string or does not parse.
    """
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def canonical_version(entry):
    """Canonical JSON of a version record, ignoring superseded_by.

    superseded_by is a forward pointer, not version content: it
    changes from null to N+1 when version N+1 is appended. The git
    history check compares this form, so appending a version does
    not read as rewriting history. Every other field is immutable.
    """
    rest = {k: v for k, v in entry.items() if k != "superseded_by"}
    return json.dumps(rest, sort_keys=True, ensure_ascii=False)


class Checker:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, record, field, message):
        self.errors.append(f"ERROR [{record}] {field}: {message}")

    def warn(self, record, field, message):
        self.warnings.append(f"WARNING [{record}] {field}: {message}")

    def check_unknown_fields(self, record_ref, obj, allowed, label):
        for key in obj:
            if key not in allowed:
                self.error(record_ref, key, f"unknown {label} field")

    def check_required_string(self, record_ref, obj, field):
        value = obj.get(field)
        if not isinstance(value, str) or not value.strip():
            self.error(record_ref, field, "missing or empty")
            return None
        return value

    def check_time(self, record_ref, obj, field, required=True):
        value = obj.get(field)
        if value is None:
            if required:
                self.error(record_ref, field, "missing")
            return None
        parsed = parse_time(value)
        if parsed is None:
            self.error(record_ref, field, f"not an ISO 8601 date/time: {value!r}")
            return None
        return parsed

    def check_evidence_list(self, record_ref, items, field, version_time):
        """Validate one evidence list. Returns True when usable."""
        if not isinstance(items, list):
            self.error(record_ref, field, "must be an array")
            return False
        ok = True
        for i, item in enumerate(items):
            ref = f"{record_ref} {field}[{i}]"
            if not isinstance(item, dict):
                self.error(ref, field, "evidence item must be an object")
                ok = False
                continue
            self.check_unknown_fields(ref, item, EVIDENCE_FIELDS, "evidence")
            for name in EVIDENCE_FIELDS:
                if name not in item:
                    self.error(ref, name, "missing")
                    ok = False
            source_url = item.get("source_url")
            if source_url is not None and (
                not isinstance(source_url, str) or not source_url.strip()
            ):
                self.error(ref, "source_url", "must be a non-empty string or null")
                ok = False
            self.check_required_string(ref, item, "publisher")
            self.check_required_string(ref, item, "excerpt")
            published = self.check_time(ref, item, "published_at", required=False)
            retrieved = self.check_time(ref, item, "retrieved_at")
            result = item.get("verification_result")
            if result not in VERIFICATION_RESULTS:
                self.error(
                    ref, "verification_result",
                    f"must be one of {sorted(VERIFICATION_RESULTS)}: {result!r}",
                )
                ok = False
            elif result == "verified" and (
                source_url is None or item.get("published_at") is None
            ):
                self.error(
                    ref, "verification_result",
                    "a verified item needs a source_url and a published_at",
                )
                ok = False
            if result == "verified" and isinstance(source_url, str) and (
                source_url.startswith("~/") or source_url.startswith("/")
            ):
                self.warn(
                    ref, "verification_result",
                    "a verified item cites a local path; confirm it is a "
                    "primary source, not the internal source document",
                )
            if published is not None and retrieved is not None:
                if retrieved < published:
                    self.error(
                        ref, "retrieved_at",
                        "retrieved_at is earlier than published_at",
                    )
                    ok = False
                if version_time is not None and retrieved > version_time:
                    self.error(
                        ref, "retrieved_at",
                        "retrieved_at is later than the version write time",
                    )
                    ok = False
        return ok

    def check_forecast_content(self, record_ref, content, version_time):
        """Validate the 21 forecast fields of one forecast (or one
        version snapshot). Returns the parsed created_at or None."""
        if not isinstance(content, dict):
            self.error(record_ref, "content", "forecast must be an object")
            return None
        self.check_unknown_fields(record_ref, content, FORECAST_FIELDS, "forecast")
        for name in FORECAST_FIELDS:
            if name not in content:
                self.error(record_ref, name, "missing")
        fid = content.get("forecast_id")
        if isinstance(fid, str) and fid:
            if not FORECAST_ID_RE.match(fid):
                self.error(
                    record_ref, "forecast_id",
                    f"must match S<season>-FC-<number>: {fid!r}",
                )
        elif fid is not None:
            self.error(record_ref, "forecast_id", "must be a string")
        self.check_required_string(record_ref, content, "proposition")
        self.check_required_string(record_ref, content, "resolution_criteria")
        self.check_required_string(record_ref, content, "reasoning_summary")
        self.check_required_string(record_ref, content, "author")
        self.check_required_string(record_ref, content, "model_version")
        self.check_required_string(record_ref, content, "method_version")
        self.check_required_string(record_ref, content, "rule_version")
        self.check_required_string(record_ref, content, "world_state_version")
        agent = content.get("agent")
        if agent is not None and (not isinstance(agent, str) or not agent.strip()):
            self.error(record_ref, "agent", "must be a non-empty string or null")
        ftype = content.get("forecast_type")
        if ftype not in FORECAST_TYPES:
            self.error(
                record_ref, "forecast_type",
                f"must be one of {sorted(FORECAST_TYPES)}: {ftype!r}",
            )
        kind = content.get("type")
        if not isinstance(kind, str) or not kind.strip():
            self.error(record_ref, "type", "must be a non-empty string")
        status = content.get("status")
        if status not in FORECAST_STATUSES:
            self.error(
                record_ref, "status",
                f"must be one of {sorted(FORECAST_STATUSES)}: {status!r}",
            )
        participants = content.get("participants")
        if not isinstance(participants, list) or not participants:
            self.error(record_ref, "participants", "must be a non-empty array")
        else:
            for p in participants:
                if isinstance(p, str):
                    if not p.strip():
                        self.error(
                            record_ref, "participants",
                            "every participant must be a non-empty string",
                        )
                elif isinstance(p, dict):
                    player = p.get("player")
                    if not isinstance(player, str) or not player.strip():
                        self.error(
                            record_ref, "participants",
                            "every participant object needs a non-empty player",
                        )
                    for key in ("persona", "persona_role", "role_in_forecast"):
                        if key in p and not isinstance(p[key], str):
                            self.error(
                                record_ref, "participants",
                                f"participant {key} must be a string",
                            )
                else:
                    self.error(
                        record_ref, "participants",
                        "every participant must be a string or an object",
                    )
        for name in ("assumptions", "counter_evidence"):
            value = content.get(name)
            if not isinstance(value, list):
                self.error(record_ref, name, "must be an array")
            elif any(not isinstance(v, str) for v in value):
                self.error(record_ref, name, "every entry must be a string")
        probability = content.get("probability")
        if not is_number(probability):
            self.error(record_ref, "probability", "must be a number")
        elif not 0.0 <= probability <= 1.0:
            self.error(
                record_ref, "probability",
                f"must be between 0 and 1: {probability!r}",
            )
        created = self.check_time(record_ref, content, "created_at")
        cutoff = self.check_time(record_ref, content, "information_cutoff")
        deadline = self.check_time(record_ref, content, "resolution_deadline")
        if created is not None and cutoff is not None and cutoff > created:
            self.error(
                record_ref, "information_cutoff",
                "information_cutoff is later than created_at",
            )
        if created is not None and deadline is not None and deadline <= created:
            self.error(
                record_ref, "resolution_deadline",
                "resolution_deadline is not later than created_at",
            )
        evidence = content.get("evidence_snapshot")
        if not isinstance(evidence, list) or not evidence:
            self.error(
                record_ref, "evidence_snapshot",
                "must be a non-empty array",
            )
        else:
            self.check_evidence_list(
                record_ref, evidence, "evidence_snapshot", version_time,
            )
        return created


def check_git_history(checker, ledger_path, current_versions):
    """Verify no version-chain record in git history was rewritten.

    current_versions maps (forecast_id, version) to the canonical JSON
    of the version record, ignoring superseded_by (see
    canonical_version). Every committed copy of the ledger is read
    and each of its version records must still exist unchanged, apart
    from the superseded_by pointer.
    """
    root = os.path.dirname(os.path.dirname(os.path.abspath(ledger_path)))
    rel = os.path.relpath(os.path.abspath(ledger_path), root)
    try:
        log = subprocess.run(
            ["git", "-C", root, "log", "--format=%H", "--", rel],
            capture_output=True, text=True, timeout=60,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        checker.warn("git", "history", "git is unavailable; history check skipped")
        return
    if log.returncode != 0:
        checker.warn("git", "history", "git log failed; history check skipped")
        return
    commits = [line.strip() for line in log.stdout.splitlines() if line.strip()]
    if not commits:
        checker.warn(
            "git", "history",
            "ledger has no committed history; history check skipped",
        )
        return
    checked = 0
    for commit in commits:
        show = subprocess.run(
            ["git", "-C", root, "show", f"{commit}:{rel}"],
            capture_output=True, text=True, timeout=60,
        )
        if show.returncode != 0:
            continue
        try:
            old = json.loads(show.stdout)
        except json.JSONDecodeError:
            checker.error(
                f"git:{commit[:8]}", "ledger",
                "committed copy is not valid JSON",
            )
            continue
        if not isinstance(old, dict) or not isinstance(old.get("versions"), list):
            continue
        for entry in old["versions"]:
            if not isinstance(entry, dict):
                continue
            key = (entry.get("forecast_id"), entry.get("version"))
            if key == (None, None):
                continue
            checked += 1
            current = current_versions.get(key)
            if current is None:
                checker.error(
                    f"git:{commit[:8]}", f"versions:{key[0]}#{key[1]}",
                    "version record from git history is missing from "
                    "the current ledger",
                )
            elif current != canonical_version(entry):
                checker.error(
                    f"git:{commit[:8]}", f"versions:{key[0]}#{key[1]}",
                    "version record from git history was rewritten",
                )
    if checked == 0:
        checker.warn(
            "git", "history",
            "no version records found in git history; nothing to compare",
        )


def validate(data, ledger_path, use_git):
    checker = Checker()
    if not isinstance(data, dict):
        checker.error("ledger", "top level", "must be a JSON object")
        return checker
    checker.check_unknown_fields("ledger", data, TOP_LEVEL_FIELDS, "top level")
    for name in TOP_LEVEL_FIELDS:
        if name not in data:
            checker.error("ledger", name, "missing top-level key")
    if data.get("schema_version") != SCHEMA_VERSION:
        checker.error(
            "ledger", "schema_version",
            f"must be {SCHEMA_VERSION!r}: {data.get('schema_version')!r}",
        )
    meta = data.get("meta")
    if not isinstance(meta, dict):
        checker.error("ledger", "meta", "must be an object")
    else:
        created = checker.check_time("meta", meta, "created")
        updated = checker.check_time("meta", meta, "updated")
        if created is not None and updated is not None and updated < created:
            checker.error("meta", "updated", "updated is earlier than created")
        note = meta.get("note")
        if note is not None and not isinstance(note, str):
            checker.error("meta", "note", "must be a string")
    forecasts = data.get("forecasts")
    resolutions = data.get("resolutions")
    versions = data.get("versions")
    if not isinstance(forecasts, list):
        checker.error("ledger", "forecasts", "must be an array")
        forecasts = []
    if not isinstance(resolutions, list):
        checker.error("ledger", "resolutions", "must be an array")
        resolutions = []
    if not isinstance(versions, list):
        checker.error("ledger", "versions", "must be an array")
        versions = []

    # Forecasts: uniqueness, fields, times, probability.
    forecast_by_id = {}
    forecast_created = {}
    for i, rec in enumerate(forecasts):
        ref = f"forecasts[{i}]"
        if not isinstance(rec, dict):
            checker.error(ref, "forecast", "forecast must be an object")
            continue
        fid = rec.get("forecast_id")
        ref = f"forecasts:{fid}" if isinstance(fid, str) and fid else ref
        if isinstance(fid, str) and fid:
            if fid in forecast_by_id:
                checker.error(ref, "forecast_id", f"duplicate forecast_id: {fid!r}")
            else:
                forecast_by_id[fid] = rec
        created = checker.check_forecast_content(ref, rec, None)
        if created is not None:
            forecast_created[fid] = created

    # Version chain: per-forecast versions, links, content equality.
    versions_by_id = {}
    current_versions = {}
    for i, entry in enumerate(versions):
        ref = f"versions[{i}]"
        if not isinstance(entry, dict):
            checker.error(ref, "version", "version record must be an object")
            continue
        fid = entry.get("forecast_id")
        ver = entry.get("version")
        ref = f"versions:{fid}#{ver}" if fid is not None else ref
        checker.check_unknown_fields(ref, entry, VERSION_FIELDS, "version")
        for name in VERSION_FIELDS:
            if name not in entry:
                checker.error(ref, name, "missing")
        if isinstance(fid, str) and fid:
            if fid not in forecast_by_id:
                checker.error(
                    ref, "forecast_id",
                    f"version references unknown forecast_id: {fid!r}",
                )
            versions_by_id.setdefault(fid, []).append(entry)
            key = (fid, ver)
            if key in current_versions:
                checker.error(ref, "version", f"duplicate version record: {key!r}")
            else:
                current_versions[key] = canonical_version(entry)
        if not isinstance(ver, int) or isinstance(ver, bool) or ver < 1:
            checker.error(ref, "version", "must be an integer >= 1")
        for name in ("supersedes", "superseded_by"):
            value = entry.get(name)
            if value is not None and (
                not isinstance(value, int) or isinstance(value, bool) or value < 1
            ):
                checker.error(ref, name, "must be an integer >= 1 or null")
        change = entry.get("change")
        if not isinstance(change, str) or not change.strip():
            checker.error(ref, "change", "missing or empty")
        version_time = checker.check_time(ref, entry, "created_at")
        content = entry.get("content")
        if not isinstance(content, dict):
            checker.error(ref, "content", "must be an object")
        else:
            checker.check_forecast_content(f"{ref} content", content, version_time)
            if isinstance(fid, str) and content.get("forecast_id") != fid:
                checker.error(
                    ref, "content.forecast_id",
                    "content forecast_id differs from the version record",
                )
    for fid, entries in versions_by_id.items():
        ref = f"versions:{fid}"
        numbers = sorted(
            e["version"] for e in entries
            if isinstance(e.get("version"), int) and not isinstance(e.get("version"), bool)
        )
        if numbers != list(range(1, len(numbers) + 1)):
            checker.error(
                ref, "version",
                f"versions must run 1..N with no gaps: {numbers!r}",
            )
            continue
        by_number = {e["version"]: e for e in entries}
        latest = max(numbers)
        for number in numbers:
            entry = by_number[number]
            entry_ref = f"versions:{fid}#{number}"
            expected_supersedes = None if number == 1 else number - 1
            if entry.get("supersedes") != expected_supersedes:
                checker.error(
                    entry_ref, "supersedes",
                    f"must be {expected_supersedes!r} for version {number}",
                )
            expected_next = None if number == latest else number + 1
            if entry.get("superseded_by") != expected_next:
                checker.error(
                    entry_ref, "superseded_by",
                    f"must be {expected_next!r} for version {number}; "
                    "superseded_by must point at an existing newer version",
                )
        times = [
            parse_time(e.get("created_at")) for e in
            (by_number[n] for n in numbers)
        ]
        if all(t is not None for t in times):
            for prev, cur in zip(times, times[1:]):
                if cur < prev:
                    checker.error(
                        ref, "created_at",
                        "a later version is dated earlier than its predecessor",
                    )
                    break
        created_values = {
            json.dumps(e["content"].get("created_at"), sort_keys=True)
            for e in entries if isinstance(e.get("content"), dict)
        }
        if len(created_values) > 1:
            checker.error(
                ref, "content.created_at",
                "created_at differs across versions; creation time is immutable",
            )
        latest_entry = by_number[latest]
        latest_content = latest_entry.get("content")
        current = forecast_by_id.get(fid)
        if isinstance(current, dict) and isinstance(latest_content, dict):
            if current != latest_content:
                differing = sorted(
                    set(current) | set(latest_content),
                    key=str,
                )
                differing = [
                    k for k in differing
                    if current.get(k) != latest_content.get(k)
                ]
                checker.error(
                    f"forecasts:{fid}", "content",
                    "forecasts entry differs from the latest version "
                    f"content in fields: {differing}",
                )
        if isinstance(latest_content, dict):
            v1_time = parse_time(by_number[1].get("created_at"))
            content_created = parse_time(latest_content.get("created_at"))
            if v1_time is not None and content_created is not None:
                if v1_time != content_created:
                    checker.error(
                        ref, "created_at",
                        "version 1 write time must equal the forecast "
                        "created_at",
                    )
    for fid in forecast_by_id:
        if fid not in versions_by_id:
            checker.error(
                f"forecasts:{fid}", "versions",
                "forecast has no version-chain record",
            )

    # Resolutions: references, review order, resolver separation,
    # score consistency, status agreement.
    resolutions_by_id = {}
    for i, rec in enumerate(resolutions):
        ref = f"resolutions[{i}]"
        if not isinstance(rec, dict):
            checker.error(ref, "resolution", "resolution must be an object")
            continue
        fid = rec.get("forecast_id")
        ref = f"resolutions:{fid}" if isinstance(fid, str) and fid else ref
        checker.check_unknown_fields(ref, rec, RESOLUTION_FIELDS, "resolution")
        for name in RESOLUTION_FIELDS:
            if name not in rec:
                checker.error(ref, name, "missing")
        forecast = forecast_by_id.get(fid) if isinstance(fid, str) else None
        if forecast is None:
            checker.error(
                ref, "forecast_id",
                f"resolution references unknown forecast_id: {fid!r}",
            )
            continue
        resolutions_by_id.setdefault(fid, []).append(rec)
        status = rec.get("resolution_status")
        if status not in RESOLUTION_STATUSES:
            checker.error(
                ref, "resolution_status",
                f"must be one of {sorted(RESOLUTION_STATUSES)}: {status!r}",
            )
        outcome = rec.get("actual_outcome")
        if status in ("hit", "miss"):
            if outcome not in (True, False):
                checker.error(
                    ref, "actual_outcome",
                    "must be true or false when the resolution status "
                    f"is {status}",
                )
        elif status == "disputed":
            if outcome is not None and outcome not in (True, False):
                checker.error(
                    ref, "actual_outcome", "must be true, false, or null")
        else:
            if outcome is not None:
                checker.error(
                    ref, "actual_outcome",
                    f"must be null when the resolution status is {status}",
                )
        resolved_at = checker.check_time(
            ref, rec, "resolved_at", required=(status != "not_yet_due"),
        )
        if status == "not_yet_due" and rec.get("resolved_at") is not None:
            checker.error(
                ref, "resolved_at",
                "must be null when the resolution status is not_yet_due",
            )
        if resolved_at is not None and forecast_created.get(fid) is not None:
            if resolved_at < forecast_created[fid]:
                checker.error(
                    ref, "resolved_at",
                    "resolved_at is earlier than the forecast created_at",
                )
        evidence = rec.get("outcome_evidence")
        if status == "not_yet_due":
            if not isinstance(evidence, list):
                checker.error(ref, "outcome_evidence", "must be an array")
        else:
            if not isinstance(evidence, list) or not evidence:
                checker.error(
                    ref, "outcome_evidence",
                    "must be a non-empty array except when not_yet_due",
                )
            else:
                checker.check_evidence_list(
                    ref, evidence, "outcome_evidence", resolved_at,
                )
        resolver = rec.get("resolver")
        if not isinstance(resolver, str) or not resolver.strip():
            checker.error(ref, "resolver", "missing or empty")
        else:
            if resolver == forecast.get("author"):
                checker.error(
                    ref, "resolver",
                    "resolver must not be the forecast author",
                )
            agent = forecast.get("agent")
            if agent is not None and resolver == agent:
                checker.error(
                    ref, "resolver",
                    "resolver must not be the forecast agent",
                )
        dispute = rec.get("dispute_status")
        if dispute not in DISPUTE_STATUSES:
            checker.error(
                ref, "dispute_status",
                f"must be one of {sorted(DISPUTE_STATUSES)}: {dispute!r}",
            )
        if status == "disputed" and dispute != "open":
            checker.error(
                ref, "dispute_status",
                "must be open when the resolution status is disputed",
            )
        if dispute == "open" and status != "disputed":
            checker.error(
                ref, "dispute_status",
                "open dispute requires the resolution status disputed",
            )
        score = rec.get("score")
        if status in ("hit", "miss"):
            if not is_number(score):
                checker.error(
                    ref, "score",
                    "must be a number when the resolution status is "
                    f"{status}",
                )
            elif not 0.0 <= score <= 1.0:
                checker.error(ref, "score", f"must be between 0 and 1: {score!r}")
            elif outcome in (True, False):
                pinned = rec.get("forecast_version")
                probability = None
                if pinned is not None:
                    entry = versions_by_id.get(fid, [])
                    match = [
                        e for e in entry if e.get("version") == pinned
                    ]
                    if match and isinstance(match[0].get("content"), dict):
                        probability = match[0]["content"].get("probability")
                if probability is None:
                    probability = forecast.get("probability")
                if is_number(probability):
                    expected = (probability - (1 if outcome else 0)) ** 2
                    if abs(score - expected) > BRIER_TOLERANCE:
                        checker.error(
                            ref, "score",
                            f"Brier score must be {expected:.4f} for "
                            f"probability {probability} and actual_outcome "
                            f"{outcome}; got {score}",
                        )
        else:
            if score is not None:
                checker.error(
                    ref, "score",
                    f"must be null when the resolution status is {status}",
                )
        review = rec.get("review")
        if review not in (True, False):
            checker.error(ref, "review", "must be true or false")
        reason = rec.get("review_reason")
        if review is True:
            if not isinstance(reason, str) or not reason.strip():
                checker.error(
                    ref, "review_reason",
                    "review_reason is required when review is true",
                )
        elif review is False:
            if reason is not None:
                checker.error(
                    ref, "review_reason",
                    "review_reason must be null when review is false",
                )
        pinned = rec.get("forecast_version")
        if pinned is not None:
            if not isinstance(pinned, int) or isinstance(pinned, bool) or pinned < 1:
                checker.error(
                    ref, "forecast_version", "must be an integer >= 1 or null",
                )
            else:
                known = {
                    e.get("version") for e in versions_by_id.get(fid, [])
                }
                if pinned not in known:
                    checker.error(
                        ref, "forecast_version",
                        f"references unknown version {pinned} of {fid}",
                    )
    for fid, entries in resolutions_by_id.items():
        ref = f"resolutions:{fid}"
        for position, rec in enumerate(entries):
            if position == 0 and rec.get("review") is not False:
                checker.error(
                    ref, "review",
                    "the first resolution must have review=false",
                )
            if position > 0 and rec.get("review") is not True:
                checker.error(
                    ref, "review",
                    "a later resolution for the same forecast must be "
                    "marked review=true with a review_reason",
                )
        latest = entries[-1]
        forecast = forecast_by_id[fid]
        expected_status = (
            "resolved"
            if latest.get("resolution_status")
            in ("hit", "miss", "indeterminate", "disputed")
            else "open"
        )
        if forecast.get("status") != expected_status:
            checker.error(
                f"forecasts:{fid}", "status",
                f"must be {expected_status!r} given the latest "
                f"resolution status "
                f"{latest.get('resolution_status')!r}",
            )
        if latest.get("dispute_status") == "resolved":
            if not any(r.get("review") is True for r in entries):
                checker.error(
                    ref, "dispute_status",
                    "resolved dispute requires a review resolution",
                )
    for fid, forecast in forecast_by_id.items():
        if forecast.get("status") == "void" and fid in resolutions_by_id:
            checker.error(
                f"forecasts:{fid}", "status",
                "a void forecast must have no resolutions",
            )
        if (
            forecast.get("status") == "open"
            and fid in resolutions_by_id
            and resolutions_by_id[fid][-1].get("resolution_status")
            in ("hit", "miss", "indeterminate", "disputed")
        ):
            checker.error(
                f"forecasts:{fid}", "status",
                "forecast is open but its latest resolution settles it",
            )

    if use_git:
        check_git_history(checker, ledger_path, current_versions)
    return checker


def main(argv=None):
    parser = argparse.ArgumentParser(description="Validate a forecast ledger.")
    parser.add_argument("ledger", nargs="?", default="forecasts/ledger.json")
    parser.add_argument("--git", action="store_true",
                        help="also verify version records against git history")
    parser.add_argument("--quiet", action="store_true",
                        help="print only the summary line")
    args = parser.parse_args(argv)
    try:
        with open(args.ledger, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"账本文件不存在：{args.ledger}", file=sys.stderr)
        return 2
    except json.JSONDecodeError as exc:
        print(f"账本文件无法解析：{exc}", file=sys.stderr)
        return 2
    checker = validate(data, args.ledger, args.git)
    if not args.quiet:
        for line in checker.warnings:
            print(line)
        for line in checker.errors:
            print(line)
    n_forecasts = len(data.get("forecasts", [])) if isinstance(data, dict) else 0
    n_resolutions = len(data.get("resolutions", [])) if isinstance(data, dict) else 0
    n_versions = len(data.get("versions", [])) if isinstance(data, dict) else 0
    if checker.errors:
        print(
            f"INVALID: {len(checker.errors)} 个错误，"
            f"{len(checker.warnings)} 个警告。预测 {n_forecasts} 条，"
            f"结算 {n_resolutions} 条，版本 {n_versions} 条。",
        )
        return 1
    print(
        f"OK: 校验通过，{len(checker.warnings)} 个警告。预测 {n_forecasts} 条，"
        f"结算 {n_resolutions} 条，版本 {n_versions} 条。",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
