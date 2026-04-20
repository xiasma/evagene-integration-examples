# Presenters: one per output format.  Each takes (table, sink) and writes.
#
# The format string is dispatched to a concrete presenter by
# `presenter_for()`; callers never branch on the format themselves.

#' Return the presenter function for a given format string.
#'
#' @param format One of "table", "csv", "json".
#' @return A function with signature `function(table, sink)`.
presenter_for <- function(format) {
  switch(format,
    table = present_table,
    csv = present_csv,
    json = present_json,
    stop(sprintf("Unknown format: %s", format))
  )
}

# --- Table (aligned, human-readable) --------------------------------------

present_table <- function(table, sink) {
  widths <- column_widths(table)
  write_line(sink, render_row(table$columns, table$columns, widths))
  for (row in table$rows) {
    write_line(sink, render_row(table$columns, row_cells(table$columns, row), widths))
  }
  invisible(NULL)
}

row_cells <- function(columns, row) {
  vapply(columns, function(col) format_cell(row[[col]]), character(1L))
}

column_widths <- function(table) {
  widths <- nchar(table$columns)
  names(widths) <- table$columns
  for (row in table$rows) {
    for (col in table$columns) {
      cell_width <- nchar(format_cell(row[[col]]))
      if (cell_width > widths[[col]]) {
        widths[[col]] <- cell_width
      }
    }
  }
  widths
}

render_row <- function(columns, cells, widths) {
  parts <- vapply(seq_along(columns), function(i) {
    formatC(cells[[i]], width = widths[[columns[[i]]]], flag = "-")
  }, character(1L))
  paste(parts, collapse = "  ")
}

# --- CSV (RFC 4180) -------------------------------------------------------

present_csv <- function(table, sink) {
  write_line(sink, csv_row(table$columns))
  for (row in table$rows) {
    write_line(sink, csv_row(row_cells(table$columns, row)))
  }
  invisible(NULL)
}

csv_row <- function(cells) {
  paste(vapply(cells, csv_escape, character(1L)), collapse = ",")
}

csv_escape <- function(value) {
  if (grepl('[",\n]', value, fixed = FALSE)) {
    sprintf('"%s"', gsub('"', '""', value, fixed = TRUE))
  } else {
    value
  }
}

# --- JSON (machine-readable) ----------------------------------------------

present_json <- function(table, sink) {
  cells <- lapply(table$rows, function(row) {
    stats::setNames(
      lapply(table$columns, function(col) json_value(row[[col]])),
      table$columns
    )
  })
  out <- list(columns = as.list(table$columns), rows = cells)
  cat(
    jsonlite::toJSON(out, auto_unbox = TRUE, pretty = TRUE, null = "null"),
    "\n",
    sep = "",
    file = sink
  )
  invisible(NULL)
}

# JSON should keep numeric probabilities as numbers, not pre-formatted strings.
# Strings in the row (Model, Counselee, lifetime summary) are passed through.
json_value <- function(value) {
  if (is.null(value)) {
    return(NA)
  }
  value
}

# --- Shared helpers -------------------------------------------------------

format_cell <- function(value) {
  if (is.null(value)) {
    return("-")
  }
  if (is.numeric(value) && length(value) == 1L && !is.na(value)) {
    return(sprintf("%.2f%%", 100 * value))
  }
  if (is.character(value) && length(value) == 1L && !is.na(value)) {
    return(value)
  }
  "-"
}

write_line <- function(sink, text) {
  cat(text, "\n", sep = "", file = sink)
}
