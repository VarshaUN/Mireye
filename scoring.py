def _val(fields, key):
    entry = fields.get(key)
    if isinstance(entry, dict):
        return entry.get("value")
    return entry


def _source(fields, key):
    entry = fields.get(key)
    if isinstance(entry, dict):
        return entry.get("source")
    return None


def _add(citations, fields, key):
    v = _val(fields, key)
    if v is not None:
        citations.append((key, v, _source(fields, key)))
    return v


def score_site(fields: dict) -> dict:
    score = 0
    reasons = []
    citations = []

    slope = _add(citations, fields, "slope_degrees")
    if slope is not None:
        if slope > 15:
            score -= 30
            reasons.append(f"steep slope ({slope:.1f}°) raises construction cost")
        elif slope > 8:
            score -= 10
            reasons.append(f"moderate slope ({slope:.1f}°)")
        else:
            score += 5
            reasons.append(f"flat, buildable terrain ({slope:.1f}°)")

    flood = _add(citations, fields, "within_floodplain_polygon")
    if flood:
        score -= 40
        reasons.append("inside FEMA floodplain")

    road_dist = _add(citations, fields, "nearest_major_road_distance_m")
    if road_dist is not None:
        if road_dist < 200:
            score += 15
            reasons.append(f"very close to a major road ({road_dist:.0f}m) — high visibility")
        elif road_dist < 500:
            score += 8
            reasons.append(f"close to a major road ({road_dist:.0f}m)")
        elif road_dist > 2000:
            score -= 10
            reasons.append(f"far from major roads ({road_dist:.0f}m)")

    poi = _add(citations, fields, "poi_count_1km")
    if poi is not None:
        if poi > 150:
            score += 25
            reasons.append(f"very high foot-traffic-adjacent density ({poi} POIs within 1km)")
        elif poi > 60:
            score += 12
            reasons.append(f"moderate POI density ({poi} within 1km)")
        elif poi < 15:
            score -= 15
            reasons.append(f"sparse POI density ({poi} within 1km), low walk-by traffic")

    residential_class = _add(citations, fields, "residential_context_class_1km")
    if residential_class:
        if residential_class in ("urban", "suburban", "mixed"):
            score += 15
            reasons.append(f"residential context: {residential_class}")
        elif residential_class == "rural":
            score -= 15
            reasons.append("rural residential context, limited walk-in demand")

    grocery = _add(citations, fields, "nearest_grocery_store_distance_m")
    if grocery is not None and grocery < 500:
        score += 10
        reasons.append(f"near a grocery store ({grocery:.0f}m) — retail clustering")

    housing = _add(citations, fields, "housing_units_within_1km")
    if housing is not None:
        if housing > 3000:
            score += 10
            reasons.append(f"dense housing nearby ({housing:,.0f} units within 1km)")
        elif housing < 200:
            score -= 10
            reasons.append(f"few housing units nearby ({housing:,.0f} within 1km)")

    zoning = _add(citations, fields, "parcel_zoning")
    if zoning:
        reasons.append(f"zoning on file: {zoning}")

    wetland = _add(citations, fields, "intersects_wetland")
    if wetland:
        score -= 20
        reasons.append("intersects a mapped wetland")

    protected = _add(citations, fields, "intersects_protected_area")
    if protected:
        score -= 25
        reasons.append("intersects a protected area")

    return {
        "score": score,
        "display_score": max(0, min(100, score + 60)),
        "reasons": reasons,
        "citations": citations,
    }