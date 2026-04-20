# Presenters: one per output format.  Each takes (rows, sink) and writes.

COLUMNS <- c(
  "Disease",
  "Inheritance",
  "CF(A)",
  "CF(B)",
  "API couple risk (A)",
  "API couple risk (B)",
  "Cross-partner offspring risk"
)

# Percentages below this threshold lose resolution at 4 d.p. -- switch to scientific.
SCIENTIFIC_THRESHOLD <- 1e-4

#' Return the presenter function for a given format string.
presenter_for <- function(format) {
  switch(format,
    table = present_table,
    csv = present_csv,
    json = present_json,
    stop(sprintf("Unknown format: %s", format))
  )
}

# --- Table (aligned, human-readable) --------------------------------------

present_table <- function(rows, sink) {
  formatted_rows <- lapply(rows, format_row_strings)
  widths <- column_widths(formatted_rows)
  write_line(sink, render_row(COLUMNS, widths))
  for (formatted in formatted_rows) {
    write_line(sink, render_row(formatted, widths))
  }
  invisible(NULL)
}

column_widths <- function(formatted_rows) {
  widths <- nchar(COLUMNS)
  for (formatted in formatted_rows) {
    widths <- pmax(widths, nchar(formatted))
  }
  widths
}

render_row <- function(cells, widths) {
  parts <- vapply(seq_along(cells), function(i) {
    formatC(cells[[i]], width = widths[[i]], flag = "-")
  }, character(1L))
  paste(parts, collapse = "  ")
}

# --- CSV (RFC 4180) -------------------------------------------------------

present_csv <- function(rows, sink) {
  write_line(sink, csv_row(COLUMNS))
  for (row in rows) {
    write_line(sink, csv_row(format_row_strings(row)))
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

present_json <- function(rows, sink) {
  json_rows <- lapply(rows, row_to_json)
  payload <- list(columns = as.list(COLUMNS), rows = json_rows)
  cat(
    jsonlite::toJSON(payload, auto_unbox = TRUE, pretty = TRUE, null = "null"),
    "\n",
    sep = "",
    file = sink
  )
  invisible(NULL)
}

row_to_json <- function(row) {
  list(
    Disease = row$disease_name,
    Inheritance = row$inheritance_pattern,
    `CF(A)` = null_to_na(row$carrier_frequency_a),
    `CF(B)` = null_to_na(row$carrier_frequency_b),
    `API couple risk (A)` = null_to_na(row$api_couple_offspring_risk_a),
    `API couple risk (B)` = null_to_na(row$api_couple_offspring_risk_b),
    `Cross-partner offspring risk` = null_to_na(row$cross_partner_offspring_risk)
  )
}

# jsonlite writes NA as null; NULL would drop the key entirely.
null_to_na <- function(value) if (is.null(value)) NA else value

# --- Shared helpers -------------------------------------------------------

format_row_strings <- function(row) {
  c(
    row$disease_name,
    row$inheritance_pattern,
    format_fraction(row$carrier_frequency_a),
    format_fraction(row$carrier_frequency_b),
    format_fraction(row$api_couple_offspring_risk_a),
    format_fraction(row$api_couple_offspring_risk_b),
    format_fraction(row$cross_partner_offspring_risk)
  )
}

format_fraction <- function(value) {
  if (is.null(value)) return("-")
  if (!is.numeric(value) || length(value) != 1L || is.na(value)) return("-")
  if (value == 0) return("0")
  if (value < SCIENTIFIC_THRESHOLD) return(sprintf("%.2e", value))
  sprintf("%.4f%%", value * 100)
}

write_line <- function(sink, text) {
  cat(text, "\n", sep = "", file = sink)
}
