"""本地材料扫描、提取、去重与题目索引。"""

from __future__ import annotations

import hashlib
import html
import re
import zipfile
from pathlib import Path
from typing import Any, Iterable
from xml.etree import ElementTree

from .errors import EmeraldError
from .planner import stable_id
from .state import atomic_write_text, now_iso

SUPPORTED = {".pdf", ".docx", ".pptx", ".txt", ".md", ".html", ".htm"}
QUESTION_RE = re.compile(
    r"^\s*(?:第\s*[一二三四五六七八九十百零〇两0-9]+\s*题|(?:Question|Problem)\s+\d+(?:\.\d+)*|\d{1,3}[.、)])\s*",
    re.IGNORECASE,
)


def _decode_text(path: Path) -> str:
    data = path.read_bytes()
    for encoding in ("utf-8", "utf-8-sig", "gb18030"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _html_text(path: Path) -> str:
    raw = _decode_text(path)
    raw = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<[^>]+>", "\n", raw)
    return html.unescape(raw)


def _zip_xml_text(path: Path, kind: str) -> str:
    lines = []
    with zipfile.ZipFile(path) as archive:
        if kind == "docx":
            names = [name for name in archive.namelist() if name == "word/document.xml"]
        else:
            names = sorted(
                (name for name in archive.namelist() if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)),
                key=lambda value: int(re.search(r"(\d+)", value).group(1)),
            )
        for index, name in enumerate(names, 1):
            root = ElementTree.fromstring(archive.read(name))
            texts = [node.text or "" for node in root.iter() if node.tag.endswith("}t")]
            if texts:
                prefix = f"[Slide {index}]" if kind == "pptx" else ""
                lines.append("\n".join(filter(None, (prefix, *texts))))
    return "\n\n".join(lines)


def _pdf_text(path: Path) -> tuple[str, list[str]]:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        return "", ["PDF 需要可选依赖 pypdf 才能提取文字；可由宿主视觉能力检查扫描页。"]
    try:
        reader = PdfReader(str(path))
        pages = []
        for index, page in enumerate(reader.pages, 1):
            pages.append(f"[Page {index}]\n{page.extract_text() or ''}")
        text = "\n\n".join(pages)
    except Exception as exc:
        return "", [f"PDF 无法解析：{exc}"]
    if len(re.sub(r"\s+", "", text)) < 20:
        return text, ["PDF 几乎没有可提取文字，可能是扫描件；请使用视觉/OCR，并核对结果。"]
    return text, []


def extract_text(path: Path) -> tuple[str, list[str]]:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return _decode_text(path), []
    if suffix in {".html", ".htm"}:
        return _html_text(path), []
    if suffix == ".docx":
        try:
            return _zip_xml_text(path, "docx"), []
        except (zipfile.BadZipFile, ElementTree.ParseError) as exc:
            return "", [f"DOCX 无法解析：{exc}"]
    if suffix == ".pptx":
        try:
            return _zip_xml_text(path, "pptx"), []
        except (zipfile.BadZipFile, ElementTree.ParseError) as exc:
            return "", [f"PPTX 无法解析：{exc}"]
    if suffix == ".pdf":
        return _pdf_text(path)
    raise EmeraldError(
        "unsupported_material",
        f"暂不支持材料格式：{suffix or '(无扩展名)'}",
        "转换为 PDF、DOCX、PPTX、TXT、Markdown 或 HTML 后重试。",
    )


def iter_material_files(inputs: Iterable[str], state_root: Path) -> list[Path]:
    files = []
    for raw in inputs:
        item = Path(raw).expanduser().resolve()
        if not item.exists():
            raise EmeraldError(
                "material_not_found",
                f"材料不存在：{item}",
                "核对路径后重新运行 ingest。",
            )
        if item.is_file():
            if item.suffix.lower() in SUPPORTED:
                files.append(item)
            continue
        for path in item.rglob("*"):
            if not path.is_file() or path.is_symlink():
                continue
            if state_root in path.parents or any(part.startswith(".") for part in path.relative_to(item).parts):
                continue
            if path.suffix.lower() in SUPPORTED:
                files.append(path)
    return sorted(set(files))


def extract_questions(
    text: str,
    source_id: str,
    subject_id: str | None = None,
    topic_id: str | None = None,
) -> list[dict[str, Any]]:
    lines = text.splitlines()
    starts = [index for index, line in enumerate(lines) if QUESTION_RE.match(line)]
    questions = []
    for position, start in enumerate(starts):
        end = starts[position + 1] if position + 1 < len(starts) else min(len(lines), start + 30)
        block = "\n".join(lines[start:end]).strip()
        if not block:
            continue
        questions.append(
            {
                "id": stable_id(source_id, str(start + 1), block[:80]),
                "source_id": source_id,
                "subject_id": subject_id,
                "topic_id": topic_id,
                "locator": f"line:{start + 1}",
                "text": block[:4000],
                "answer": None,
                "source_grounded": True,
            }
        )
    return questions


def ingest_files(
    paths: Iterable[Path],
    state_root: Path,
    existing_sources: list[dict[str, Any]],
    existing_questions: list[dict[str, Any]],
    evidence_level: str,
    subject_id: str | None = None,
    topic_id: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    by_digest = {item.get("sha256"): item for item in existing_sources}
    added = []
    warnings = []
    materials_dir = state_root / "materials"
    materials_dir.mkdir(exist_ok=True)
    for path in paths:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in by_digest:
            existing = by_digest[digest]
            changed_binding = False
            if subject_id and existing.get("subject_id") != subject_id:
                existing["subject_id"] = subject_id
                changed_binding = True
            if topic_id and existing.get("topic_id") != topic_id:
                existing["topic_id"] = topic_id
                changed_binding = True
            if changed_binding:
                for question in existing_questions:
                    if question.get("source_id") == existing.get("id"):
                        question["subject_id"] = subject_id
                        question["topic_id"] = topic_id
                warnings.append(f"更新重复材料的科目/专题绑定：{path}")
            else:
                warnings.append(f"跳过重复材料：{path}")
            continue
        text, file_warnings = extract_text(path)
        source_id = stable_id(digest, path.name)
        derived_path = materials_dir / f"{source_id}.md"
        header = (
            f"# 材料提取：{path.name}\n\n"
            f"- 原始路径：`{path}`\n"
            f"- SHA-256：`{digest}`\n"
            f"- 证据等级：`{evidence_level}`\n\n"
            "---\n\n"
        )
        atomic_write_text(derived_path, header + text)
        questions = extract_questions(text, source_id, subject_id, topic_id)
        record = {
            "id": source_id,
            "path": str(path),
            "derived_path": str(derived_path),
            "name": path.name,
            "extension": path.suffix.lower(),
            "size_bytes": path.stat().st_size,
            "sha256": digest,
            "evidence_level": evidence_level,
            "subject_id": subject_id,
            "topic_id": topic_id,
            "ingested_at": now_iso(),
            "text_chars": len(text),
            "question_count": len(questions),
            "warnings": file_warnings,
        }
        existing_sources.append(record)
        existing_questions.extend(questions)
        by_digest[digest] = record
        added.append(record)
        warnings.extend(f"{path.name}: {warning}" for warning in file_warnings)
    return existing_sources, existing_questions, added, warnings
