# -*- coding: utf-8 -*-
"""
המרת DXF → שכבות SHP מסודרות לפי תקן מפ"י
מעבד את כל קבצי ה-DXF ושומר את כל המידע הטבלאי
הרץ בתוך QGIS: Plugins → Python Console → Open Editor → Run
"""

import os, re
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsVectorFileWriter,
    QgsCoordinateReferenceSystem, QgsCoordinateTransformContext,
    QgsWkbTypes, QgsField, QgsFields, QgsFeature, QgsGeometry,
    QgsSingleSymbolRenderer, QgsMarkerSymbol, QgsLineSymbol, QgsFillSymbol,
    QgsLayerTreeGroup,
)
from qgis.PyQt.QtCore import QVariant

# ============================================================
# קבצי DXF לעיבוד
# ============================================================
DXF_FILES = [
    r"C:\Ayala Projects\Neot Kdomim\dwg_export\survey.dxf",  # מדידת כל השמורה
    r"C:\Ayala Projects\Neot Kdomim\dwg_export\ps.dxf",       # תוכנית מצב
]
OUTPUT_DIR = r"C:\Ayala Projects\Neot Kdomim\shp_export_FINAL"
CRS        = QgsCoordinateReferenceSystem("EPSG:2039")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# ============================================================
# מיפוי קודי מפ"י → (נושא, תיאור עברי)
# ============================================================
CODES = {
    "M1502": ("boundaries",    "קו גבול חלקה"),
    "M1503": ("boundaries",    "נקודת גבול"),
    "M1504": ("boundaries",    "אבן גבול"),
    "M1505": ("boundaries",    "גבול אזור"),
    "M1506": ("boundaries",    "גבול שיפוט"),
    "M1507": ("boundaries",    "גבול אחר"),
    "M1509": ("boundaries",    "גבול שטח פרטי"),
    "M1510": ("boundaries",    "גבול מגרש"),
    "M1520": ("boundaries",    "קו מגבלה"),
    "M2100": ("buildings",     "מבנה"),
    "M2103": ("buildings",     "כניסה / מרפסת"),
    "M2299": ("buildings",     "מבנה מיוחד"),
    "M2200": ("fences_walls",  "גדר כללית"),
    "M2202": ("fences_walls",  "גדר תייל"),
    "M2207": ("fences_walls",  "חומה / קיר אבן"),
    "M2209": ("fences_walls",  "קיר תמך"),
    "M2210": ("fences_walls",  "גדר בטון"),
    "M2213": ("fences_walls",  "גדר רשת"),
    "M2401": ("roads_paths",   "כביש סלול"),
    "M2403": ("roads_paths",   "דרך עפר ראשית"),
    "M2404": ("roads_paths",   "דרך עפר משנית"),
    "M2405": ("roads_paths",   "שביל הליכה"),
    "M2406": ("roads_paths",   "שביל רכיבה"),
    "M2407": ("roads_paths",   "מדרכה"),
    "M2411": ("roads_paths",   "סימון כביש"),
    "M2412": ("roads_paths",   "מחסום / שער"),
    "M2414": ("roads_paths",   "גשר"),
    "M2417": ("roads_paths",   "מדרגות"),
    "M2430": ("roads_paths",   "שפת דרך"),
    "M2519": ("water",         "מאגר מים"),
    "M2601": ("water",         "גוף מים עומד"),
    "M2602": ("water",         "נחל / ואדי"),
    "M2603": ("water",         "בור / בריכה"),
    "M2604": ("water",         "באר"),
    "M2605": ("water",         "תעלת השקיה"),
    "M2606": ("water",         "מקור / עין"),
    "M2612": ("water",         "קו מים"),
    "M2801": ("trees",         "עץ בודד"),
    "M2802": ("trees",         "קבוצת עצים / חורשה"),
    "M2803": ("trees",         "שיח בודד"),
    "M2804": ("trees",         "שטח שיחים"),
    "M2805": ("trees",         "עץ פרי"),
    "M2806": ("trees",         "כרם / מטע"),
    "M2809": ("trees",         "צמחייה מיוחדת"),
    "M3001": ("topography",    "קו גובה"),
    "M3004": ("topography",    "קו גובה ראשי"),
    "M3005": ("topography",    "נקודת גובה"),
    "M3901": ("survey_points", "נקודת בקרה ראשית"),
    "M3903": ("survey_points", "נקודת פוליגון"),
    "M3906": ("survey_points", "נקודת מדידה"),
    "M3909": ("survey_points", "נקודת GPS"),
    "M4008": ("infrastructure","בנייה תת-קרקעית"),
    "M4402": ("infrastructure","עמוד חשמל"),
    "M4410": ("infrastructure","קו חשמל עילי"),
    "M4411": ("infrastructure","ארון חשמל"),
    "M4601": ("infrastructure","קו תקשורת"),
    "M4611": ("infrastructure","עמוד תקשורת"),
    "M4612": ("infrastructure","ארון תקשורת"),
    "M4901": ("annotations",   "כיתוב טקסט"),
    "M4903": ("annotations",   "מספר חלקה"),
    "M4904": ("annotations",   "תגית גובה"),
    "M5202": ("terrain",       "שטח סלעי"),
    "M5203": ("terrain",       "סלע בולט"),
    "M5205": ("terrain",       "גוש סלע"),
    "M5211": ("terrain",       "מצוק"),
    "M5212": ("terrain",       "שיפוע חד"),
    "M5214": ("terrain",       "ערוץ שחיקה"),
    "M5235": ("terrain",       "שטח חשוף"),
    "M5250": ("terrain",       "חפירה / מילוי"),
    "M6011": ("heritage",      "אתר ארכיאולוגי"),
    "M6021": ("heritage",      "מבנה היסטורי"),
    "M6351": ("heritage",      "גבול אתר מוגן"),
    "M6371": ("heritage",      "ממצא מיוחד"),
}

def classify(code):
    c = (code or "").strip()
    if c in CODES:
        return CODES[c]
    for k, v in CODES.items():
        if c.startswith(k[:4]):
            return v
    return ("other", c or "לא מזוהה")

def geom_suffix(wkb):
    flat = QgsWkbTypes.flatType(wkb)
    return {
        QgsWkbTypes.Point:           "point",
        QgsWkbTypes.MultiPoint:      "point",
        QgsWkbTypes.LineString:      "line",
        QgsWkbTypes.MultiLineString: "line",
        QgsWkbTypes.Polygon:         "polygon",
        QgsWkbTypes.MultiPolygon:    "polygon",
    }.get(flat, "other")

# ============================================================
# סימבולוגיה
# ============================================================
STYLE = {
    "trees":          ("#2d6a2d", 3.0, "circle"),
    "boundaries":     ("#8B0000", 1.2, "square"),
    "roads_paths":    ("#b5651d", 1.8, "diamond"),
    "water":          ("#1565C0", 1.8, "circle"),
    "buildings":      ("#CC3300", 1.2, "square"),
    "fences_walls":   ("#555555", 1.0, "square"),
    "topography":     ("#8B7355", 0.6, "circle"),
    "terrain":        ("#A0522D", 0.8, "square"),
    "infrastructure": ("#7B1FA2", 1.0, "triangle"),
    "survey_points":  ("#E65100", 3.5, "cross"),
    "heritage":       ("#F9A825", 4.0, "star"),
    "annotations":    ("#212121", 0.6, "circle"),
    "other":          ("#AAAAAA", 0.5, "circle"),
}

def apply_style(vlayer, topic):
    s = STYLE.get(topic, STYLE["other"])
    color, size, shape = s
    geom = QgsWkbTypes.geometryType(vlayer.wkbType())
    if geom == QgsWkbTypes.PointGeometry:
        sym = QgsMarkerSymbol.createSimple({
            "name": shape, "color": color,
            "size": str(size), "outline_style": "no"})
    elif geom == QgsWkbTypes.LineGeometry:
        sym = QgsLineSymbol.createSimple({
            "color": color, "width": str(size),
            "capstyle": "round", "joinstyle": "round"})
    else:
        sym = QgsFillSymbol.createSimple({
            "color": color + "55",
            "outline_color": color, "outline_width": "0.6"})
    vlayer.setRenderer(QgsSingleSymbolRenderer(sym))
    vlayer.triggerRepaint()

# ============================================================
# שדות נוספים שנוסיף לכל SHP
# ============================================================
EXTRA_FIELDS = [
    QgsField("m_code",   QVariant.String, len=10),   # קוד מפ"י
    QgsField("desc_he",  QVariant.String, len=80),   # תיאור עברי
    QgsField("src_file", QVariant.String, len=30),   # מקור (survey/ps)
]

# ============================================================
# איסוף פיצ'רים מכל קבצי ה-DXF
# ============================================================
# buckets[key] = {
#   "base_fields": QgsFields,  # שדות מקוריים מה-DXF
#   "wkb": int,
#   "topic": str,
#   "rows": [(QgsFeature, m_code, desc_he, src_name)]
# }
buckets = {}

for dxf_path in DXF_FILES:
    if not os.path.exists(dxf_path):
        print(f"[!] לא נמצא: {dxf_path}")
        continue

    src_name = os.path.splitext(os.path.basename(dxf_path))[0]
    print(f"\n{'='*55}")
    print(f"קובץ: {src_name}")

    # גלה תת-שכבות
    probe = QgsVectorLayer(dxf_path, "probe", "ogr")
    sublayers = probe.dataProvider().subLayers()
    del probe

    for sub in sublayers:
        parts = sub.split("!!::!!")
        if len(parts) < 2:
            continue
        lyr_name = parts[1]
        uri      = f"{dxf_path}|layername={lyr_name}"
        lyr      = QgsVectorLayer(uri, lyr_name, "ogr")

        if not lyr.isValid() or lyr.featureCount() == 0:
            continue

        # מצא שדה שם שכבה
        fnames    = [f.name() for f in lyr.fields()]
        layer_fld = next((f for f in fnames
                          if f.lower() in ["layer","lyr","dwg_layer"]), None)

        print(f"  {lyr_name}: {lyr.featureCount():,} objects "
              f"| שדות: {fnames}")

        for feat in lyr.getFeatures():
            geom = feat.geometry()
            if not geom or geom.isEmpty():
                continue

            code        = str(feat[layer_fld]).strip() if layer_fld else ""
            topic, desc = classify(code)
            gsuf        = geom_suffix(geom.wkbType())
            key         = f"{topic}_{gsuf}"

            if key not in buckets:
                buckets[key] = {
                    "base_fields": lyr.fields(),
                    "wkb":   geom.wkbType(),
                    "topic": topic,
                    "rows":  [],
                }
            buckets[key]["rows"].append((feat, code, desc, src_name))

        del lyr

# ============================================================
# כתיבת SHP — שדות מקוריים + שדות נוספים
# ============================================================
print(f"\n{'='*55}")
print("כותב קבצי SHP...\n")

ctx     = QgsCoordinateTransformContext()
written = []

for key in sorted(buckets.keys()):
    b    = buckets[key]
    rows = b["rows"]
    if not rows:
        continue

    topic = b["topic"]
    safe  = re.sub(r"[^\w]", "_", key)
    path  = os.path.join(OUTPUT_DIR, f"{safe}.shp")

    # בנה שדות: שדות מקוריים + שדות נוספים
    out_fields = QgsFields()
    for f in b["base_fields"]:
        out_fields.append(f)
    for f in EXTRA_FIELDS:
        out_fields.append(f)

    opts = QgsVectorFileWriter.SaveVectorOptions()
    opts.driverName   = "ESRI Shapefile"
    opts.fileEncoding = "UTF-8"

    w = QgsVectorFileWriter.create(path, out_fields, b["wkb"], CRS, ctx, opts)
    if w.hasError() != QgsVectorFileWriter.NoError:
        print(f"  ERR {safe}: {w.errorMessage()}")
        del w; continue

    n_base = b["base_fields"].count()
    for feat, code, desc, src in rows:
        new_feat = QgsFeature(out_fields)
        new_feat.setGeometry(feat.geometry())
        # העתק שדות מקוריים
        for i in range(min(n_base, feat.fields().count())):
            try:
                new_feat.setAttribute(i, feat.attribute(i))
            except Exception:
                pass
        # שדות נוספים
        new_feat.setAttribute(n_base,     code[:10])
        new_feat.setAttribute(n_base + 1, desc[:80])
        new_feat.setAttribute(n_base + 2, src[:30])
        w.addFeature(new_feat)
    del w

    # טען ל-QGIS + סימבולוגיה
    vlayer = QgsVectorLayer(path, safe, "ogr")
    if vlayer.isValid():
        apply_style(vlayer, topic)
        QgsProject.instance().addMapLayer(vlayer)
        written.append((safe, len(rows), topic))
        print(f"  OK {safe:<35} {len(rows):>8,}")

# ============================================================
# ארגון בקבוצות לפי נושא
# ============================================================
root   = QgsProject.instance().layerTreeRoot()
topics = ["trees","boundaries","roads_paths","water","buildings",
          "fences_walls","topography","terrain","infrastructure",
          "survey_points","heritage","annotations","other"]

for topic in topics:
    layers_in_topic = [
        QgsProject.instance().mapLayersByName(s)[0]
        for s, c, t in written
        if t == topic and QgsProject.instance().mapLayersByName(s)
    ]
    if not layers_in_topic:
        continue
    grp = root.addGroup(topic)
    for lyr in layers_in_topic:
        node = root.findLayer(lyr.id())
        if node:
            clone = node.clone()
            grp.insertChildNode(0, clone)
            root.removeChildNode(node)

# ============================================================
# סיכום
# ============================================================
print(f"\n{'='*55}")
print(f"DONE — {len(written)} שכבות SHP נוצרו")
print(f"תיקייה: {OUTPUT_DIR}\n")

totals = {}
for s, c, t in written:
    totals[t] = totals.get(t, 0) + c
for t in topics:
    if t in totals:
        print(f"  {t:<20} {totals[t]:>8,} objects")
