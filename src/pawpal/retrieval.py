import math
import re
from dataclasses import dataclass
from pathlib import Path

_TOKEN_RE = re.compile(r"[a-z0-9]+")

DEFAULT_KNOWLEDGE_DIR = Path(__file__).resolve().parents[2] / "knowledge"


def _normalize(token: str) -> str:
    """Crude singular/plural stemmer (e.g. 'dogs' -> 'dog') so simple keyword
    overlap isn't defeated by pluralization."""
    if len(token) > 3 and token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def _tokenize(text: str) -> list[str]:
    return [_normalize(t) for t in _TOKEN_RE.findall(text.lower())]


@dataclass
class KnowledgeChunk:
    source: str
    heading: str
    text: str

    @property
    def citation(self) -> str:
        return f"{self.source} -> {self.heading}"

    @property
    def snippet(self) -> str:
        """First full sentence of the chunk body, with hard-wrapped newlines
        collapsed to spaces (source .md files wrap prose at ~80 chars, so a
        naive `text.splitlines()[0]` can cut a sentence off mid-word)."""
        flat = " ".join(self.text.split())
        period_idx = flat.find(". ")
        if period_idx != -1:
            return flat[: period_idx + 1]
        return flat


def load_knowledge_base(directory: Path = DEFAULT_KNOWLEDGE_DIR) -> list[KnowledgeChunk]:
    """Parse every .md file in `directory` into chunks split on '## ' headings.
    Each file may contribute multiple chunks (multi-source, multi-section retrieval)."""
    chunks: list[KnowledgeChunk] = []
    for path in sorted(directory.glob("*.md")):
        content = path.read_text(encoding="utf-8")
        sections = re.split(r"^## ", content, flags=re.MULTILINE)
        for section in sections[1:]:
            lines = section.strip().splitlines()
            heading = lines[0].strip()
            body = "\n".join(lines[1:]).strip()
            chunks.append(KnowledgeChunk(source=path.name, heading=heading, text=body))
    return chunks


def _document_frequencies(chunks: list[KnowledgeChunk]) -> dict[str, int]:
    df: dict[str, int] = {}
    for chunk in chunks:
        tokens = set(_tokenize(chunk.text)) | set(_tokenize(chunk.heading))
        for t in tokens:
            df[t] = df.get(t, 0) + 1
    return df


def retrieve(query: str, chunks: list[KnowledgeChunk], k: int = 3) -> list[tuple[KnowledgeChunk, float]]:
    """Score chunks against the query using presence-based TF-IDF: each distinct
    matching token contributes idf(token) = log((1+N)/(1+df)) + 1, so common words
    that appear across most of the corpus (e.g. 'dog' in a pet-care KB) count for
    less than distinctive words (e.g. 'litter', 'feeding'). Heading matches count
    double. Returns the top-k chunks with score > 0, highest first."""
    if not chunks:
        return []
    query_tokens = set(_tokenize(query))
    n_chunks = len(chunks)
    df = _document_frequencies(chunks)

    def idf(token: str) -> float:
        return math.log((1 + n_chunks) / (1 + df.get(token, 0))) + 1

    scored: list[tuple[KnowledgeChunk, float]] = []
    for chunk in chunks:
        body_tokens = set(_tokenize(chunk.text))
        heading_tokens = set(_tokenize(chunk.heading))
        score = sum(idf(t) for t in body_tokens if t in query_tokens)
        score += 2 * sum(idf(t) for t in heading_tokens if t in query_tokens)
        if score > 0:
            scored.append((chunk, round(score, 2)))
    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:k]
