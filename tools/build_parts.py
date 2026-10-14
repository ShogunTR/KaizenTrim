"""kaizen-meta CSV dosyalarından sitenin okuduğu parts.json'u üretir.

Kullanım:
    python tools/build_parts.py "<kaizen-meta klasörü>" parts.json
"""
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

ANGLES = ["on", "arka", "ust", "sol45", "sag45"]


def read_csv(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def brand_model(path):
    segs = [s for s in re.split(r"[\\/]", path or "") if s]
    i = 1
    if len(segs) > 2 and segs[1].upper().startswith("SMALL PARTS"):
        i = 2
    brand = segs[i] if len(segs) > i else ""
    # Otomobil/Marka/Model/Parça: model, parça klasöründen önceki parçadır
    model = segs[i + 1] if len(segs) > i + 2 else ""
    return brand, model


def main(meta, out):
    meta = Path(meta)
    rows = read_csv(meta / "ilan_sirasi_v3_5foto.csv")

    shop = {}
    log = meta / "shopier_log.csv"
    if log.exists():
        for r in read_csv(log):
            sid = (r.get("id") or "").strip()
            if not sid:
                m = re.search(r"(\d{6,})", r.get("url") or "")
                sid = m.group(1) if m else ""
            if r.get("sira") and sid:
                shop[r["sira"].strip()] = int(sid)

    prefixes, parts, odd = {}, [], 0
    for r in rows:
        urls = [(r.get(f"url{i}") or "").strip() for i in range(1, 6)]
        urls = [u for u in urls if u]
        if not urls:
            continue
        brand, model = brand_model(r.get("parca_yolu"))
        if not brand:
            brand = (r.get("marka") or "").title()
        title = re.sub(r"\s*-\s*3D Bask[ıi]\s*$", "", (r.get("baslik_tr") or "").strip())

        # url1..5 aynı tabandan "-on.png", "-arka.png" ... ile ayrılıyorsa kısa yaz
        img = urls
        cut = urls[0].find("/main/")
        if cut > 0 and urls[0].endswith("-on.png"):
            prefix = urls[0][: cut + 6]
            base = urls[0][cut + 6 : -len("-on.png")]
            if urls == [f"{prefix}{base}-{a}.png" for a in ANGLES]:
                key = prefixes.setdefault(prefix, str(len(prefixes)))
                img = base
        if isinstance(img, list):
            odd += 1
            key = ""

        sira = (r.get("sira") or "").strip()
        parts.append([
            int(sira) if sira.isdigit() else sira,
            "O" if (r.get("kategori") or "").startswith("Oto") else "M",
            brand, model, title, (r.get("slug") or "").strip(), key, img, shop.get(sira, 0),
        ])

    data = {"img": {v: k for k, v in prefixes.items()}, "parts": parts}
    Path(out).write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")

    cats = Counter(p[1] for p in parts)
    print(f"{len(parts)} parça yazıldı ({cats['O']} otomobil, {cats['M']} motosiklet), "
          f"{len({p[2] for p in parts})} marka, Shopier linki olmayan: {sum(1 for p in parts if not p[8])}, "
          f"standart dışı görsel adı: {odd}")
    print("Görsel kökleri:", list(prefixes))
    for p in parts[:3]:
        print(p)


if __name__ == "__main__":
    main(*sys.argv[1:3])
