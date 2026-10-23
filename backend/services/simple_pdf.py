def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")

def _encode(value: str) -> str:
    return _escape(value).encode("cp1252", errors="replace").decode("cp1252")

def render_pdf(lines: list[str]) -> bytes:
    pages = _paginate(lines, 46)
    if not pages:
        pages = [[""]]
    return _document(pages)

def _paginate(lines: list[str], size: int) -> list[list[str]]:
    pages: list[list[str]] = []
    chunk: list[str] = []
    for line in lines:
        chunk.append(line)
        if len(chunk) >= size:
            pages.append(chunk)
            chunk = []
    if chunk:
        pages.append(chunk)
    return pages

def _page_stream(lines: list[str]) -> bytes:
    commands = ["BT", "/F1 12 Tf", "48 800 Td", "16 TL"]
    for line in lines:
        text = line[2:] if line.startswith("# ") else line
        if line.startswith("# "):
            commands.append("/F1 16 Tf")
        commands.append(f"({_encode(text)}) Tj")
        if line.startswith("# "):
            commands.append("/F1 12 Tf")
        commands.append("T*")
    commands.append("ET")
    return "\n".join(commands).encode("cp1252", errors="replace")

def _document(pages: list[list[str]]) -> bytes:
    streams = [_page_stream(page) for page in pages]
    count = len(pages)
    objects: list[bytes] = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    kids = " ".join(f"{3 + index * 2} 0 R" for index in range(count))
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {count} >>".encode())
    for index, stream in enumerate(streams):
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
                f"/Contents {4 + index * 2} 0 R /Resources << /Font << /F1 {3 + count * 2} 0 R >> >> >>"
            ).encode()
        )
        objects.append(f"<< /Length {len(stream)} >>\nstream\n".encode() + stream + b"\nendstream")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")

    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode())
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(
        (f"trailer << /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n").encode()
    )
    return bytes(output)
