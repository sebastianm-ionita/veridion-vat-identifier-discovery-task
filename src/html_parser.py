from bs4 import BeautifulSoup
from typing import Optional

import re
from bs4 import BeautifulSoup
from typing import Optional


class VRNMismatchError(Exception):
    """Result page contains other VRN than the VRN searched for."""


def _normalize_vrn(vrn: str) -> str:
    if not vrn:
        return ""
    clean = re.sub(r"[^A-Za-z0-9]", "", vrn).upper()
    return clean.removeprefix("GB")


def _heading_text(target: str):
    return lambda t: t is not None and t.strip() == target


def parse_known_page(html: str, vrn: str) -> tuple[Optional[str], Optional[str]]:
    soup = BeautifulSoup(html, "html.parser")

    # check we are on the good page
    title = soup.find("h1", class_="govuk-panel__title",
                      string=_heading_text("Valid UK VAT number"))
    if not title:
        return (None, None)

    # shown vrn has to be the searched vrn
    panel_body = soup.find("div", class_="govuk-panel__body")
    if panel_body:
        shown = _normalize_vrn(panel_body.get_text(strip=True))
        if shown and shown != _normalize_vrn(vrn):
            raise VRNMismatchError(f"Searched {vrn}, Shown {shown}")

    name = None
    name_heading = soup.find("h3", string=_heading_text("Registered business name"))
    if name_heading:
        p = name_heading.find_next_sibling("p")
        if p:
            name = p.get_text(strip=True) or None

    address = None
    addr_heading = soup.find("h3", string=_heading_text("Registered business address"))
    if addr_heading:
        p = addr_heading.find_next_sibling("p")
        if p:
            lines = [s for s in p.stripped_strings]
            address = "\n".join(lines) if lines else None

    return (name, address)


def extract_postcode(address: Optional[str]) -> Optional[str]:
    if not address:
        return None

    lines = address.split("\n")
    if len(lines) < 2:
        return None

    candidate = lines[-2].strip().upper()
    return candidate if re.fullmatch(r"[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2}", candidate) else None


