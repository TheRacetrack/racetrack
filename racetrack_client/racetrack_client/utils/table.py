from typing import List


def print_table(table: List[List[str]]):
    """
    Print padded table to stdout
    :param table: list of rows (row -> column -> cell)
    """
    cols_num: int = max([len(row) for row in table])

    col_widths: List[int] = []
    for col_index in range(cols_num):
        max_width = 0
        for row in table:
            cell = row[col_index] or ''
            max_width = max(max_width, len(cell))
        col_widths.append(max_width)

    for row in table:
        row_values: List[str] = []
        for col_index in range(cols_num):
            padding = col_widths[col_index]
            cell = (row[col_index] or '').ljust(padding)
            row_values.append(cell)
        print('   '.join(row_values))
