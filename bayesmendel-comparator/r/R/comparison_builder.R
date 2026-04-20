# Pure transform: list of per-model RiskResult payloads -> a ComparisonTable.
#
# ComparisonTable has:
#   $columns  -- ordered character vector of column names
#   $rows     -- list of named lists; each row is a row in the table
#
# The schema is checked strictly: a silent default here would mask a
# server-side change and leave the caller reasoning over stale numbers.

FIXED_COLUMNS <- c("Model", "Counselee", "Any carrier")
CARRIER_ANY_KEY <- "Pr(Being a carrier)"
LIFETIME_COLUMN <- "Lifetime risk @max-age"

#' Raise a response_schema_error condition.
#' @noRd
stop_schema <- function(message) {
  stop(structure(
    list(message = message, call = sys.call(-1)),
    class = c("response_schema_error", "error", "condition")
  ))
}

#' Build a ComparisonTable from a list of RiskResult payloads.
#'
#' @param payloads Named list whose names are model names (in display order)
#'   and whose values are parsed JSON responses from `calculate_risk()`.
#' @return A `comparison_table` list with fields `columns` and `rows`.
build_comparison <- function(payloads) {
  require_non_empty_named_list(payloads, "payloads")

  gene_columns <- gene_column_order(payloads)
  columns <- c(FIXED_COLUMNS, gene_columns, LIFETIME_COLUMN)

  rows <- lapply(names(payloads), function(model_name) {
    build_row(model_name, payloads[[model_name]], gene_columns)
  })

  structure(
    list(columns = columns, rows = rows),
    class = "comparison_table"
  )
}

build_row <- function(model_name, payload, gene_columns) {
  require_object(payload, sprintf("payload for %s", model_name))
  carrier_probs <- require_named_number_dict(payload, "carrier_probabilities")

  row <- list()
  row[["Model"]] <- model_name
  row[["Counselee"]] <- optional_string(payload, "counselee_name")
  row[["Any carrier"]] <- carrier_probs[[CARRIER_ANY_KEY]]  # may be NULL
  for (gene in gene_columns) {
    row[[gene]] <- carrier_probs[[gene]]  # NULL for models that omit it
  }
  row[[LIFETIME_COLUMN]] <- summarise_lifetime_risks(payload)
  row
}

# --- Column discovery -----------------------------------------------------

gene_column_order <- function(payloads) {
  seen <- character(0)
  for (payload in payloads) {
    carrier_probs <- payload$carrier_probabilities
    if (is.list(carrier_probs) && !is.null(names(carrier_probs))) {
      for (key in names(carrier_probs)) {
        if (key != CARRIER_ANY_KEY && !(key %in% seen)) {
          seen <- c(seen, key)
        }
      }
    }
  }
  seen
}

# --- Lifetime-risk summary ------------------------------------------------

#' Pick the oldest future-risk row and render its risks as "Label X.YZ%; ...".
#' Returns NULL (i.e. no value in the row) if there are no future risks.
summarise_lifetime_risks <- function(payload) {
  future_risks <- payload$future_risks
  if (!is.list(future_risks) || length(future_risks) == 0L) {
    return(NULL)
  }

  oldest <- oldest_future_risk(future_risks)
  risks <- oldest$risks
  if (!is.list(risks) || is.null(names(risks)) || length(risks) == 0L) {
    return(NULL)
  }

  parts <- vapply(names(risks), function(label) {
    sprintf("%s %s", label, format_percent(risks[[label]]))
  }, character(1L))
  paste(parts, collapse = "; ")
}

oldest_future_risk <- function(future_risks) {
  ages <- vapply(future_risks, function(entry) {
    age <- entry$age
    if (is.numeric(age) && length(age) == 1L) as.integer(age) else NA_integer_
  }, integer(1L))
  if (all(is.na(ages))) {
    stop_schema("future_risks contains no numeric ages")
  }
  future_risks[[which.max(ages)]]
}

# --- Formatting -----------------------------------------------------------

#' Format a probability in [0,1] as a percentage to two decimals.
format_percent <- function(value) {
  if (is.null(value) || !is.numeric(value) || length(value) != 1L || is.na(value)) {
    return("-")
  }
  sprintf("%.2f%%", 100 * value)
}

# --- Schema guards --------------------------------------------------------

require_object <- function(value, label) {
  if (!is.list(value) || (length(value) > 0 && is.null(names(value)))) {
    stop_schema(sprintf("%s is not an object", label))
  }
  invisible(value)
}

require_named_number_dict <- function(payload, key) {
  value <- payload[[key]]
  if (!is.list(value) || (length(value) > 0 && is.null(names(value)))) {
    stop_schema(sprintf("field '%s' is missing or not an object", key))
  }
  for (name in names(value)) {
    inner <- value[[name]]
    if (!is.numeric(inner) || length(inner) != 1L || is.na(inner)) {
      stop_schema(sprintf("field '%s[\"%s\"]' is not a number", key, name))
    }
  }
  value
}

require_non_empty_named_list <- function(value, label) {
  if (!is.list(value) || length(value) == 0L || is.null(names(value))) {
    stop_schema(sprintf("%s must be a non-empty named list", label))
  }
  invisible(value)
}

optional_string <- function(container, key) {
  value <- container[[key]]
  if (!is.character(value) || length(value) != 1L || is.na(value)) {
    return("")
  }
  value
}
