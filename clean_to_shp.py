"""
clean_to_shp.py  —  v3
-----------------------
ייצוא שכבות DXF לקבצי SHP לפי קטגוריות:
- מסנן PaperSpace, תיבות טקסט, גיאומטריה שגויה ורעש
- מאחד כל קודי-M לקטגוריה אחת (vegetation, buildings וכו')
- שומר את כל שדות הטבלה לסימבולוגיה (m_code, desc_he וכו')
- מייצר קובץ _point/_line/_polygon לכל קטגוריה עם נתונים

הרצה: QGIS → Plugins → Python Console → Show Editor → Open → Run
"""

import os, re
from qgis.core import (
    QgsProject, QgsVectorLayer, QgsVectorFileWriter,
    QgsCoordinateTransformContext, QgsFeature, QgsField
)
from qgis.PyQt.QtCore import QVariant

def find_field(fields, *names):
    """חיפוש שדה ללא תלות ב-case"""
    lower_names = [n.lower() for n in names]
    for i, field in enumerate(fields):
        if field.name().lower() in lower_names:
            return i
    return -1

# ══════════════════════════════════════════════════════════════════════
#  הגדרות
# ══════════════════════════════════════════════════════════════════════
OUTPUT_DIR = r"C:\Ayala Projects\Neot Kdomim\SHP_Clean"
MIN_AREA      = 0.01  # מ"ר מינימלי לפוליגונים (מסנן רעש)
MIN_LENGTH    = 0.01  # מ' מינימלי לקווים
MAX_HOLE_AREA = 30    # מ"ר — חורים קטנים מזה (תיבות טקסט) יימולאו

# ══════════════════════════════════════════════════════════════════════
#  תקן מפ"י — מיפוי קוד-M → קטגוריה
# ══════════════════════════════════════════════════════════════════════
CATEGORY_MAP = {
    # צמחייה ועצים — M12xx
    "M12": "vegetation",
    # טופוגרפיה — M15xx (קווי גובה, נקודות גובה)
    "M15": "topography",
    # מבנים — M21xx
    "M21": "buildings", "M2299": "buildings",
    # דרכים — M22xx, M23xx, M24xx
    "M22": "roads_paths", "M23": "roads_paths", "M24": "roads_paths",
    # תשתיות — M25xx, M26xx
    "M25": "infrastructure", "M26": "infrastructure",
    # שטח פתוח / טופוגרפיה — M27xx, M28xx
    "M27": "topography", "M28": "topography",
    # גדרות וקירות — M30xx
    "M30": "fences_walls",
    # מורשת ועתיקות — M39xx
    "M39": "heritage",
    # גבולות — M40xx, M46xx
    "M40": "boundaries", "M46": "boundaries",
    # נקודות מדידה — M49xx
    "M49": "survey_points",
    # מים — M52xx
    "M52": "water",
    # אנוטציות — M44xx
    "M44": "annotations",
    # אחר
    "M60": "other", "M63": "other",
}

# ══════════════════════════════════════════════════════════════════════
#  תיאורים עבריים לפי קוד M (לשדה desc_he כשחסר)
# ══════════════════════════════════════════════════════════════════════
MCODE_DESC = {
    # טופוגרפיה
    "M1502":"קו גובה","M1503":"קו גובה אינדקס","M1504":"קו גובה משוער",
    "M1505":"שפת תעלה","M1506":"קו גובה","M1507":"נקודת גובה",
    "M1509":"קו שפה","M1510":"שפת מדרגה","M1520":"ממשק שטח",
    # צמחייה
    "M1211":"עצי פרי","M1212":"עצי נוי","M1213":"עצי יער","M1214":"עצי צל",
    "M1221":"שיחים","M1231":"כיסוי עשבוני","M1241":"כרם","M1251":"פרדס",
    # מבנים
    "M2100":"מבנה","M2101":"מבנה קבע","M2102":"מבנה זמני",
    "M2103":"מבנה תת-קרקעי","M2104":"מבנה חקלאי","M2299":"מבנה מדוד",
    # דרכים
    "M2200":"כביש","M2201":"כביש מהיר","M2202":"כביש ראשי",
    "M2207":"שפת כביש","M2209":"ציר דרך","M2210":"מסלול",
    "M2213":"נתיב הולכי רגל",
    "M2401":"כביש סלול","M2402":"כביש אספלט","M2403":"דרך עפר",
    "M2404":"מדרגות","M2405":"שביל סלול","M2406":"שביל עפר",
    "M2407":"שביל","M2411":"חניה","M2412":"אי תנועה",
    "M2414":"סימון כביש","M2417":"שפת מדרכה","M2430":"מדרכה",
    # תשתיות
    "M2519":"בור ביקורת",
    "M2601":"צנרת מים","M2602":"צנרת ביוב","M2603":"קו חשמל",
    "M2604":"קו תקשורת","M2605":"קו גז","M2606":"ניקוז","M2612":"תשתית כללית",
    # שטח / טופוגרפיה
    "M2801":"קו שפה","M2802":"קיר תמך","M2803":"קיר אבן",
    "M2804":"סלע","M2805":"מצוק","M2806":"שיפוע","M2809":"שקע",
    # גדרות וקירות
    "M3001":"גדר","M3002":"גדר תיל","M3003":"גדר רשת",
    "M3004":"קיר","M3005":"קיר תמך",
    # מורשת
    "M3901":"אתר מורשת","M3903":"מבנה היסטורי",
    "M3906":"ממצא ארכיאולוגי","M3909":"מורשת אחרת",
    # גבולות
    "M4008":"גבול מגרש","M4601":"קו גבול",
    "M4611":"גבול תכנוני","M4612":"גבול שיפוט",
    # נקודות מדידה
    "M4901":"נקודת מדידה","M4903":"בנצ'מרק","M4904":"נקודת GPS",
    # מים
    "M5202":"מעיין","M5203":"באר","M5211":"נחל",
    "M5212":"תעלת מים","M5214":"גוף מים","M5250":"בריכה",
    # אחר
    "M6011":"גבול שמורה","M6021":"גדר שמורה","M6351":"מסלול טיול",
}

# שמות עבריים לקטגוריות
CATEGORY_HE = {
    "vegetation":    "צמחייה",
    "buildings":     "מבנים",
    "roads_paths":   "דרכים_ושבילים",
    "infrastructure":"תשתיות",
    "topography":    "טופוגרפיה",
    "fences_walls":  "גדרות_וקירות",
    "heritage":      "מורשת",
    "boundaries":    "גבולות",
    "survey_points": "נקודות_מדידה",
    "water":         "מים",
    "annotations":   "אנוטציות",
    "other":         "אחר",
    "sheets":        "גיליונות",
}

def get_category(m_code):
    """מחזיר קטגוריה לפי קוד M"""
    if not m_code or m_code in ("", "None", "NULL"):
        return "other"
    m = str(m_code).strip().upper()
    if not m.startswith("M"):
        m = "M" + m
    # בדוק התאמה מדויקת תחילה (למשל M2299)
    if m in CATEGORY_MAP:
        return CATEGORY_MAP[m]
    # בדוק לפי 3 תווים ראשונים (M + 2 ספרות)
    prefix3 = m[:3]
    if prefix3 in CATEGORY_MAP:
        return CATEGORY_MAP[prefix3]
    # בדוק לפי 2 תווים ראשונים (M + 1 ספרה)
    prefix2 = m[:2]
    if prefix2 in CATEGORY_MAP:
        return CATEGORY_MAP[prefix2]
    return "other"

# ══════════════════════════════════════════════════════════════════════
#  פונקציית שמירה תואמת לכל גרסאות QGIS
# ══════════════════════════════════════════════════════════════════════
def save_layer(lyr, path):
    try:
        opts = QgsVectorFileWriter.SaveVectorOptions()
        opts.driverName   = "ESRI Shapefile"
        opts.fileEncoding = "UTF-8"
        result = QgsVectorFileWriter.writeAsVectorFormatV3(
            lyr, path, QgsCoordinateTransformContext(), opts)
        return result[0]
    except AttributeError:
        pass
    try:
        err, _ = QgsVectorFileWriter.writeAsVectorFormat(
            lyr, path, "UTF-8", lyr.crs(), "ESRI Shapefile")
        return err
    except Exception as e:
        print(f"    ⚠ שגיאה: {e}")
        return 1

# ══════════════════════════════════════════════════════════════════════
#  איסוף פיצ'רים מכל השכבות
# ══════════════════════════════════════════════════════════════════════
os.makedirs(OUTPUT_DIR, exist_ok=True)

# מבנה: buckets[category][geom_type] = (fields, [features], crs)
buckets      = {}
sheet_feats  = []
sheet_fields = None
sheet_crs    = None

project = QgsProject.instance()
total_in = total_out = total_skip = 0

for layer in project.mapLayers().values():
    if not isinstance(layer, QgsVectorLayer):
        continue

    # ── דלג שכבות שכבר יצאו (מקורן בתיקיית הפלט) ───────────────
    src = layer.dataProvider().dataSourceUri().replace("\\","/").lower()
    if OUTPUT_DIR.replace("\\","/").lower() in src:
        continue

    geom_type = layer.geometryType()
    geom_name = {0:"Point", 1:"LineString", 2:"Polygon"}.get(geom_type)
    if not geom_name:
        continue

    fields     = layer.fields()
    paper_idx  = find_field(fields, "PaperSpace", "paperspace")
    mcode_idx  = find_field(fields, "m_code", "mcode")
    layer_idx  = find_field(fields, "Layer", "layer", "LAYER")
    sub_idx    = find_field(fields, "SubClasses", "subclasses")
    text_idx   = find_field(fields, "Text", "text", "name")
    etype_idx  = find_field(fields, "etype", "EType", "EntityType")
    crs        = layer.crs()

    ref_idx = mcode_idx if mcode_idx >= 0 else layer_idx  # קוד-M לקטגוריה

    for feat in layer.getFeatures():
        total_in += 1
        geom = feat.geometry()

        # ── סינון PaperSpace ────────────────────────────────────────
        if paper_idx >= 0:
            ps = feat.attribute(paper_idx)
            if ps is not None and str(ps).strip() not in ("","NULL","None","False","0"):
                # שמור גיליונות (PSBorderM) בנפרד
                mval = str(feat.attribute(mcode_idx) if mcode_idx>=0 else "").strip()
                if "PSBorder" in mval or "PSBorderM" in (str(feat.attribute(layer_idx)) if layer_idx>=0 else ""):
                    sheet_feats.append(feat)
                    sheet_fields = fields
                    sheet_crs    = crs
                else:
                    total_skip += 1
                continue

        # ── סינון תיבות טקסט ────────────────────────────────────────
        # שיטה 1: לפי SubClasses (ייבוא ישן)
        if sub_idx >= 0:
            sub = str(feat.attribute(sub_idx) or "")
            is_text = any(t in sub for t in ("AcDbText","AcDbMText","AcDbAttDef"))
            is_text_block = (
                "AcDbBlockReference" in sub and text_idx >= 0 and
                str(feat.attribute(text_idx) or "").strip()
                not in ("","None","NULL","DOTS","CONTINUOUS","BYLAYER","BYBLOCK")
            )
            if is_text or is_text_block:
                total_skip += 1
                continue
        # שיטה 2: לפי etype (ייבוא GPKG) — TEXT=1, MTEXT=2, ATTDEF=10, ATTRIB=11
        if etype_idx >= 0:
            try:
                if int(feat.attribute(etype_idx) or -1) in (1, 2, 10, 11):
                    total_skip += 1
                    continue
            except (TypeError, ValueError):
                pass

        # ── סינון גיאומטריה ─────────────────────────────────────────
        if geom is None or geom.isEmpty() or geom.isNull():
            total_skip += 1
            continue
        if not geom.isGeosValid():
            geom = geom.makeValid()
            if geom is None or geom.isEmpty():
                total_skip += 1
                continue
        if geom_type == 2 and geom.area()   < MIN_AREA:
            total_skip += 1
            continue
        if geom_type == 1 and geom.length() < MIN_LENGTH:
            total_skip += 1
            continue

        # ── מילוי חורים קטנים בפוליגונים (תיבות תגית) ──────────────
        # חורים קטנים מ-MAX_HOLE_AREA נוצרו מתיבות טקסט שהיו inner rings
        if geom_type == 2:
            filled = geom.removeInteriorRings(MAX_HOLE_AREA)
            if filled and not filled.isEmpty():
                geom = filled

        # ── קביעת קטגוריה ───────────────────────────────────────────
        # עדיפות: שדה m_code → שדה Layer → שם שכבת QGIS
        m_code = ""
        if ref_idx >= 0:
            m_code = str(feat.attribute(ref_idx) or "").strip()
        if not m_code or m_code in ("NULL", "None"):
            m_code = layer.name().strip()  # שם שכבת QGIS (M1506, M2299 וכו')
        cat = get_category(m_code)

        key = (cat, geom_type)
        if key not in buckets:
            buckets[key] = {
                "fields":    fields,
                "crs":       crs,
                "feats":     [],
                "geom_name": {0:"Point",1:"LineString",2:"Polygon"}.get(geom_type)
            }
        buckets[key]["feats"].append(feat)
        total_out += 1

# ══════════════════════════════════════════════════════════════════════
#  שמירת גיליונות
# ══════════════════════════════════════════════════════════════════════
print("\n" + "="*70)
print("  תוצאות ייצוא שכבות")
print("="*70)

if sheet_feats and sheet_fields and sheet_crs:
    sm = QgsVectorLayer(f"Polygon?crs={sheet_crs.authid()}", "sheets", "memory")
    sp = sm.dataProvider()
    sp.addAttributes(sheet_fields)
    sm.updateFields()
    sp.addFeatures(sheet_feats)
    sm.updateExtents()
    err = save_layer(sm, os.path.join(OUTPUT_DIR, "sheets_גיליונות.shp"))
    mark = "✅" if err == QgsVectorFileWriter.NoError else "❌"
    print(f"  {mark}  {'sheets_גיליונות':35s} | {len(sheet_feats):5d} גיליונות")

# ══════════════════════════════════════════════════════════════════════
#  שמירת קטגוריות
# ══════════════════════════════════════════════════════════════════════
geom_suffix = {0:"_point", 1:"_line", 2:"_polygon"}

for (cat, geom_type), data in sorted(buckets.items()):
    feats    = data["feats"]
    fields   = data["fields"]
    crs      = data["crs"]
    suffix   = geom_suffix.get(geom_type,"")
    gname    = data.get("geom_name") or {0:"Point",1:"LineString",2:"Polygon"}.get(geom_type)
    he_name  = CATEGORY_HE.get(cat, cat)

    mem = QgsVectorLayer(f"{gname}?crs={crs.authid()}", cat, "memory")
    prov = mem.dataProvider()

    # הוסף את כל השדות המקוריים
    prov.addAttributes(fields)

    # הוסף שדה desc_he אם לא קיים
    existing = [f.name().lower() for f in fields]
    has_desc   = "desc_he"  in existing
    has_mcode  = "m_code"   in existing
    has_layer  = "layer"    in existing
    if not has_desc:
        prov.addAttributes([QgsField("desc_he",  QVariant.String, len=80)])
    if not has_mcode and has_layer:
        prov.addAttributes([QgsField("m_code",   QVariant.String, len=10)])

    mem.updateFields()
    desc_out_idx  = mem.fields().indexOf("desc_he")
    mcode_out_idx = mem.fields().indexOf("m_code")
    layer_in_idx  = fields.indexOf("layer") if fields.indexOf("layer") >= 0 else fields.indexOf("Layer")

    # העתק פיצ'רים ומלא desc_he + m_code אם חסרים
    new_feats = []
    for feat in feats:
        new_f = QgsFeature(mem.fields())
        # העתק גיאומטריה
        new_f.setGeometry(feat.geometry())
        # העתק ערכי שדות מקוריים
        for i, field in enumerate(fields):
            idx = mem.fields().indexOf(field.name())
            if idx >= 0:
                new_f.setAttribute(idx, feat.attribute(i))
        # קבע m_code
        raw_code = ""
        if layer_in_idx >= 0:
            raw_code = str(feat.attribute(layer_in_idx) or "").strip()
        if not raw_code or raw_code in ("NULL","None"):
            raw_code = data.get("layer_name","")
        if not has_mcode and mcode_out_idx >= 0:
            new_f.setAttribute(mcode_out_idx, raw_code)
        # קבע desc_he
        if not has_desc and desc_out_idx >= 0:
            m_up = raw_code.upper()
            if not m_up.startswith("M"):
                m_up = "M" + m_up
            desc = MCODE_DESC.get(m_up, "")
            new_f.setAttribute(desc_out_idx, desc)
        new_feats.append(new_f)

    prov.addFeatures(new_feats)
    mem.updateExtents()

    fname    = f"{cat}{suffix}_{he_name}.shp"
    out_path = os.path.join(OUTPUT_DIR, fname)
    err      = save_layer(mem, out_path)
    mark     = "✅" if err == QgsVectorFileWriter.NoError else "❌"
    print(f"  {mark}  {fname:50s} | {len(feats):5d} פיצ׳רים")

    # ── טעינה לפרויקט QGIS עם סימבולוגיה קטגורית לפי desc_he ──────
    if err == QgsVectorFileWriter.NoError:
        shp_layer = QgsVectorLayer(out_path, f"{cat}{suffix}_{he_name}", "ogr")
        if shp_layer.isValid():
            # סימבולוגיה קטגורית לפי desc_he
            from qgis.core import QgsCategorizedSymbolRenderer, QgsRendererCategory, QgsSymbol
            import random
            desc_field = "desc_he"
            if shp_layer.fields().indexOf(desc_field) >= 0:
                unique_vals = shp_layer.uniqueValues(shp_layer.fields().indexOf(desc_field))
                categories = []
                for val in sorted([v for v in unique_vals if v]):
                    sym = QgsSymbol.defaultSymbol(shp_layer.geometryType())
                    r,g,b = random.randint(50,220), random.randint(50,220), random.randint(50,220)
                    sym.setColor(__import__('qgis.PyQt.QtGui', fromlist=['QColor']).QColor(r,g,b))
                    categories.append(QgsRendererCategory(val, sym, str(val)))
                renderer = QgsCategorizedSymbolRenderer(desc_field, categories)
                shp_layer.setRenderer(renderer)
            try:
                QgsProject.instance().addMapLayer(shp_layer)
            except Exception:
                pass  # שכבה כבר קיימת בפרויקט

# ══════════════════════════════════════════════════════════════════════
#  סיכום
# ══════════════════════════════════════════════════════════════════════
print("="*70)
print(f"\n  נכנסו:  {total_in:,}  פיצ׳רים")
print(f"  יצאו:   {total_out:,}  פיצ׳רים")
print(f"  סוננו:  {total_skip:,}  פיצ׳רים")
print(f"\n📁 קבצי SHP נשמרו ב: {OUTPUT_DIR}")
print("✔  הסתיים")
