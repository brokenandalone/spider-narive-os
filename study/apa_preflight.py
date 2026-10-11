"""Conservative, completely offline checks of an owner-entered APA draft.

No source lookup, bibliographic invention, citation repair, official grading,
or promise of APA compliance. Source matching is deliberately heuristic.
"""
import re

SOURCE_MARKERS = ("[SOURCE NEEDED]", "[CITATION NEEDED]", "[VERIFY SOURCE]",
                  "[VERIFY CITATION]", "[REFERENCE NEEDED]")
YEAR = r"(?:19|20)\d{2}[a-z]?"
MAX_TEXT = 120_000


def _clean_lines(references):
    if isinstance(references, str):
        lines = references.splitlines()
    else:
        lines = list(references)
    return [str(line).strip() for line in lines if str(line).strip()]


def _leading_author(reference):
    """Look for a conventional surname or organization author, not full validation."""
    match = re.match(r"^\s*([\w][\w'’\-. ]{1,100}?)\s*,\s*[A-Z]\.", reference)
    if match:
        name = match.group(1).strip().split()[-1]
        return name.casefold()
    match = re.match(r"^\s*([\w][\w'’\-. ]{2,100}?)\.\s*\(\s*" + YEAR + r"\s*\)", reference)
    if match:
        return match.group(1).strip().casefold()
    return None


def _reference_keys(reference):
    author = _leading_author(reference)
    year_match = re.search(r"\(\s*(" + YEAR + r")\s*\)", reference, re.I)
    if author and year_match:
        return (author, year_match.group(1).casefold())
    return None


def _body_citations(body):
    """Find common surname/year citations without claiming complete APA parsing."""
    citations = set()
    author = r"([A-Z][A-Za-z'’\-]{1,49})"
    coauthor = r"(?:\s+(?:&|and)\s+[A-Z][A-Za-z'’\-]+|\s+et al\.)?"
    # Narrative: Smith (2021), Smith and Jones (2021), Smith et al. (2021).
    narrative = r"\b" + author + coauthor + r"\s*\(\s*(" + YEAR + r")\s*\)"
    for match in re.finditer(narrative, body):
        citations.add((match.group(1).casefold(), match.group(2).casefold()))
    # Parenthetical: (Smith, 2021), (Smith & Jones, 2021),
    # (Smith et al., 2021) and (Smith, 2021; Brown, 2022).
    for parenthetical in re.findall(r"\([^()]{1,450}\)", body):
        for fragment in parenthetical[1:-1].split(";"):
            match = re.match(
                r"\s*" + author + coauthor + r"\s*,\s*(" + YEAR + r")\b",
                fragment.strip(),
            )
            if match:
                citations.add((match.group(1).casefold(), match.group(2).casefold()))
    return sorted(citations)

def analyze_apa_preflight(*, draft, references, instructions=""):
    """Return observed signals and warnings, not a judgment of validity."""
    draft = str(draft)
    instructions = str(instructions)
    refs = _clean_lines(references)
    if len(draft) > MAX_TEXT or len(instructions) > 24_000:
        raise ValueError("Draft or directions exceed the bounded offline review size.")
    if not draft.strip():
        raise ValueError("Enter a draft before checking citations.")
    if len(refs) > 300 or sum(len(s) for s in refs) > MAX_TEXT:
        raise ValueError("Reference entries exceed the offline review limits.")
    found = _body_citations(draft)
    known = {_reference_keys(ref) for ref in refs} - {None}
    missing = sorted(set(found) - known)
    unrecognized = sum(_reference_keys(ref) is None for ref in refs)
    normalized = [re.sub(r"\s+", " ", ref).strip().casefold() for ref in refs]
    duplicate_count = len(normalized) - len(set(normalized))
    markers = sum(draft.upper().count(placeholder) for placeholder in SOURCE_MARKERS)
    words = len(re.findall(r"\b[\w]+(?:['’][\w]+)?\b", draft, re.UNICODE))
    warnings = []
    if not refs:
        warnings.append("No owner-entered reference entries are present.")
    if duplicate_count:
        warnings.append(f"{duplicate_count} identical reference-line duplicate(s) detected.")
    if markers:
        warnings.append(f"{markers} source/citation verification placeholder(s) remain.")
    for surname, year in missing[:20]:
        warnings.append(
            f"Possible unmatched in-text author-date citation: {surname.title()} ({year}).")
    if len(missing) > 20:
        warnings.append("Additional possible unmatched citations were omitted from display.")
    if refs and not found:
        warnings.append(
            "No simple surname/year citation pattern detected in the draft. "
            "Check narrative, group-author, and unusual citations manually.")
    if unrecognized:
        warnings.append(
            f"{unrecognized} reference line(s) do not match a basic author/year pattern; "
            "check manually, especially organizational authors and nonstandard entries.")
    if len(refs) and not missing and found:
        warnings.append("Matched surname/year strings do NOT establish source accuracy or APA correctness.")
    warnings.append("Confirm title page, double spacing, indentation, references and instructor requirements in the exported Word file.")
    return {
        "word_count": words,
        "reference_lines": len(refs),
        "citation_pairs": found,
        "unmatched_pairs": missing,
        "unrecognized_references": unrecognized,
        "duplicate_references": duplicate_count,
        "markers": markers,
        "warnings": warnings,
    }


def format_apa_preflight(report):
    parts = [
        "STUDY | APA & SOURCE PREFLIGHT (OFFLINE, HEURISTIC)",
        f"Draft words: {report['word_count']}",
        f"Reference lines entered: {report['reference_lines']}",
        f"Possible author/date citations observed: {len(report['citation_pairs'])}",
        f"Possible unmatched author/date pairs: {len(report['unmatched_pairs'])}",
        f"Unresolved source placeholders: {report['markers']}",
        "",
        "CHECK BEFORE SUBMISSION:",
    ]
    parts += ["• " + warning for warning in report["warnings"]]
    parts += [
        "", "This is NOT an APA validator, source-verification service, grade, "
        "plagiarism check, or proof your paper meets university rules."
    ]
    return "\n".join(parts)
