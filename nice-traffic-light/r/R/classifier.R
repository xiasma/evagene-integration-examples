# Parse the Evagene /risk/calculate response into a NICE outcome.
#
# Strict by design -- a silent default would mask a server-side schema
# change and leave the caller reasoning over stale assumptions.

known_categories <- c("near_population", "moderate", "high")

#' Raise a response_schema_error condition.
#' @noRd
stop_schema <- function(message) {
  stop(structure(
    list(message = message, call = sys.call(-1)),
    class = c("response_schema_error", "error", "condition")
  ))
}

#' Parse an Evagene risk-calculation response into a nice_outcome.
#'
#' @param payload A named list (e.g. from `jsonlite::fromJSON(..., simplifyVector = FALSE)`).
#' @return A `nice_outcome` list with fields: counselee_name, category
#'   (one of "near_population", "moderate", "high"),
#'   refer_for_genetics_assessment, triggers, notes.
classify_nice_response <- function(payload) {
  require_object(payload, "response")
  cancer_risk <- require_object_field(payload, "cancer_risk")

  outcome <- list(
    counselee_name = optional_string(payload, "counselee_name"),
    category = parse_category(require_string_field(cancer_risk, "nice_category")),
    refer_for_genetics_assessment = require_boolean_field(cancer_risk, "nice_refer_genetics"),
    triggers = require_string_list_field(cancer_risk, "nice_triggers"),
    notes = require_string_list_field(cancer_risk, "notes")
  )
  class(outcome) <- "nice_outcome"
  outcome
}

parse_category <- function(raw) {
  if (!raw %in% known_categories) {
    stop_schema(sprintf("Unknown NICE category: '%s'", raw))
  }
  raw
}

require_object <- function(value, label) {
  if (!is.list(value) || (length(value) > 0 && is.null(names(value)))) {
    stop_schema(sprintf("%s is not an object", label))
  }
  invisible(value)
}

require_object_field <- function(container, key) {
  value <- container[[key]]
  if (!is.list(value) || is.null(names(value))) {
    stop_schema(sprintf("field '%s' is missing or not an object", key))
  }
  value
}

require_string_field <- function(container, key) {
  value <- container[[key]]
  if (!is.character(value) || length(value) != 1L || is.na(value)) {
    stop_schema(sprintf("field '%s' is missing or not a string", key))
  }
  value
}

require_boolean_field <- function(container, key) {
  value <- container[[key]]
  if (!is.logical(value) || length(value) != 1L || is.na(value)) {
    stop_schema(sprintf("field '%s' is missing or not a boolean", key))
  }
  value
}

require_string_list_field <- function(container, key) {
  value <- container[[key]]
  if (is.null(value)) {
    return(character(0))
  }
  if (is.list(value)) {
    # jsonlite(simplifyVector = FALSE) returns a list of length-1 character
    # scalars for a JSON string array.  We must validate each element
    # explicitly -- unlist() would silently coerce mixed types.
    is_string_scalar <- vapply(
      value,
      function(item) is.character(item) && length(item) == 1L && !is.na(item),
      logical(1L)
    )
    if (!all(is_string_scalar)) {
      stop_schema(sprintf("field '%s' is not a list of strings", key))
    }
    return(vapply(value, as.character, character(1L)))
  }
  if (!is.character(value) || any(is.na(value))) {
    stop_schema(sprintf("field '%s' is not a list of strings", key))
  }
  value
}

optional_string <- function(container, key) {
  value <- container[[key]]
  if (!is.character(value) || length(value) != 1L || is.na(value)) {
    return("")
  }
  value
}
