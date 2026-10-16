entry = current_data.get("measurement")
if entry["status"] != "current":
    raise ValueError("The saved measurement is not current")
measurement = entry["value"]
selected = measurement["selected"]
row_index, col_index = selected["logical_row_col"]
consumed = {
    "value": measurement,
    "logical_column": col_index,
    "round_trip_pixel_top_left": [measurement["row_starts"][row_index],
                                   measurement["col_starts"][col_index]],
    "round_trip_matches": selected["pixel_top_left"] ==
        [measurement["row_starts"][row_index], measurement["col_starts"][col_index]],
}
