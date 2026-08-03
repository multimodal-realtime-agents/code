"""Handle file artifacts returned by A2A agents.

The current A2A SDK represents inline files as raw parts and remote files as
URL parts. A client that can handle both forms can save generated images,
documents, or other binary outputs without assuming every response is text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from a2a.helpers import new_raw_artifact, new_url_artifact


@dataclass(frozen=True)
class ReceivedFile:
    filename: str
    media_type: str
    data: bytes | None = None
    url: str | None = None


def inline_file_artifact(name: str, data: bytes, media_type: str):
    return new_raw_artifact(
        name=name,
        raw=data,
        media_type=media_type,
        filename=name,
    )


def url_file_artifact(name: str, url: str, media_type: str):
    return new_url_artifact(
        name=name,
        url=url,
        media_type=media_type,
        filename=name,
    )


def extract_files(artifact) -> list[ReceivedFile]:
    files: list[ReceivedFile] = []
    for part in artifact.parts:
        if part.HasField("raw"):
            files.append(
                ReceivedFile(
                    filename=part.filename,
                    media_type=part.media_type,
                    data=part.raw,
                )
            )
        if part.HasField("url"):
            files.append(
                ReceivedFile(
                    filename=part.filename,
                    media_type=part.media_type,
                    url=part.url,
                )
            )
    return files


def safe_output_name(filename: str) -> str:
    candidate = re.split(r"[\\/]+", filename)[-1]
    allowed = r"[^A-Za-z0-9._-]+"
    candidate = re.sub(allowed, "_", candidate)
    candidate = candidate.strip("._")
    if not candidate:
        candidate = f"artifact-{uuid4().hex}"
    return f"received_{candidate}"


def save_inline_files(artifact, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_paths: list[Path] = []

    for received_file in extract_files(artifact):
        if received_file.data is None:
            continue
        output_path = output_dir / safe_output_name(received_file.filename)
        output_path.write_bytes(received_file.data)
        saved_paths.append(output_path)

    return saved_paths
