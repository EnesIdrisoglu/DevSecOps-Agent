"""Platform kanıtından ayrı, opsiyonel web araması."""

from __future__ import annotations

import json
import re
from urllib.parse import quote
from urllib.request import Request, urlopen


def search_cve(cve: str, timeout: float = 5.0) -> dict[str, object]:
    """NVD API'den özet döndürür; ağ hatasında güvenli ve açık sonuç verir."""
    if not re.fullmatch(r"CVE-\d{4}-\d{4,}", cve.strip(), re.IGNORECASE):
        return {"ok": False, "message": "Geçerli bir CVE kimliği bekleniyor."}
    url = "https://services.nvd.nist.gov/rest/json/cves/2.0?cveId=" + quote(cve.upper())
    try:
        with urlopen(Request(url, headers={"Accept": "application/json", "User-Agent": "devsecops-ai-agent/0.1"}), timeout=timeout) as response:
            payload = json.load(response)
        vulnerabilities = payload.get("vulnerabilities", [])
        if not vulnerabilities:
            return {"ok": True, "source": "NVD", "message": "NVD kaydında sonuç bulunamadı."}
        item = vulnerabilities[0].get("cve", {})
        descriptions = item.get("descriptions", [])
        return {"ok": True, "source": "NVD", "id": item.get("id"), "summary": next((d["value"] for d in descriptions if d.get("lang") == "en"), "Açıklama yok.")}
    except Exception as exc:
        return {"ok": False, "message": f"Web araması kullanılamadı: {exc.__class__.__name__}. Yerel kanıtla sınırlanıldı."}
