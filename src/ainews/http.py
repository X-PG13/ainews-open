from __future__ import annotations

import json
import mimetypes
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional
from urllib.request import Request, urlopen


@dataclass
class DownloadedBinary:
    data: bytes
    content_type: str = "application/octet-stream"
    filename: str = "download.bin"


def fetch_text(url: str, timeout: int, user_agent: str) -> str:
    request = Request(url, headers={"User-Agent": user_agent})
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return response.read().decode(charset, errors="replace")


def request_json(
    url: str,
    *,
    timeout: int,
    user_agent: str,
    method: str = "GET",
    payload: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    request_headers = {
        "Accept": "application/json",
        "User-Agent": user_agent,
    }
    data = None
    if payload is not None:
        request_headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")
    if headers:
        request_headers.update(headers)

    request = Request(
        url,
        data=data,
        headers=request_headers,
        method=method.upper(),
    )
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return json.loads(response.read().decode(charset, errors="replace"))


def fetch_json(
    url: str,
    *,
    timeout: int,
    user_agent: str,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    return request_json(
        url,
        timeout=timeout,
        user_agent=user_agent,
        method="GET",
        headers=headers,
    )


def fetch_binary(url: str, timeout: int, user_agent: str) -> DownloadedBinary:
    request = Request(url, headers={"User-Agent": user_agent})
    with urlopen(request, timeout=timeout) as response:
        content_type = response.headers.get_content_type() or "application/octet-stream"
        path_name = Path(getattr(response, "url", url)).name or "download.bin"
        filename = path_name if "." in path_name else _filename_from_type(path_name, content_type)
        return DownloadedBinary(
            data=response.read(),
            content_type=content_type,
            filename=filename,
        )


def post_multipart(
    url: str,
    *,
    files: Dict[str, tuple[str, bytes, str]],
    fields: Optional[Dict[str, str]] = None,
    timeout: int,
    user_agent: str,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    boundary = f"----ainews-{uuid.uuid4().hex}"
    body = bytearray()

    for key, value in (fields or {}).items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
        body.extend(str(value).encode("utf-8"))
        body.extend(b"\r\n")

    for key, (filename, payload, content_type) in files.items():
        body.extend(f"--{boundary}\r\n".encode("utf-8"))
        body.extend(
            (
                f'Content-Disposition: form-data; name="{key}"; filename="{filename}"\r\n'
                f"Content-Type: {content_type or 'application/octet-stream'}\r\n\r\n"
            ).encode("utf-8")
        )
        body.extend(payload)
        body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode("utf-8"))

    request_headers = {
        "Accept": "application/json",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "User-Agent": user_agent,
    }
    if headers:
        request_headers.update(headers)

    request = Request(
        url,
        data=bytes(body),
        headers=request_headers,
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:
        charset = response.headers.get_content_charset() or "utf-8"
        return json.loads(response.read().decode(charset, errors="replace"))


def post_json(
    url: str,
    payload: Dict[str, Any],
    *,
    timeout: int,
    user_agent: str,
    headers: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    return request_json(
        url,
        timeout=timeout,
        user_agent=user_agent,
        method="POST",
        payload=payload,
        headers=headers,
    )


def _filename_from_type(stem: str, content_type: str) -> str:
    extension = mimetypes.guess_extension(content_type) or ".bin"
    base_name = stem or "download"
    return base_name if "." in base_name else f"{base_name}{extension}"
