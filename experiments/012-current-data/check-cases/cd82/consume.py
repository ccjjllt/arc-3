entry = current_data.get("measurement")
if entry["status"] != "current":
    raise ValueError("The saved measurement is not current")
measurement = entry["value"]
bounds = measurement["bbox_tlbr_inclusive"]
consumed = {
    "value": measurement,
    "height": bounds[2] - bounds[0] + 1,
    "width": bounds[3] - bounds[1] + 1,
    "filled_fraction": measurement["pixel_count"] /
        ((bounds[2] - bounds[0] + 1) * (bounds[3] - bounds[1] + 1)),
}
