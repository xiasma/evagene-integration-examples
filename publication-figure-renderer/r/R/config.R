# Immutable configuration from CLI args + environment.

DEFAULT_BASE_URL <- "https://evagene.net"
UUID_PATTERN <- "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
LABEL_STYLES <- c("initials", "generation-number", "off")
DEFAULT_LABEL_STYLE <- "generation-number"

#' Raise a config_error condition.
#' @noRd
stop_config <- function(message) {
  stop(structure(
    list(message = message, call = sys.call(-1)),
    class = c("config_error", "error", "condition")
  ))
}

#' Load configuration from CLI args + environment.
#'
#' @param argv Character vector of CLI arguments (without program name).
#' @param env Named list of environment variables; callers coming from
#'   `Sys.getenv()` should use `as.list(Sys.getenv())`.
#' @return A named list with fields base_url, api_key, pedigree_id,
#'   output_path, deidentify, label_style, width, height.
load_config <- function(argv, env) {
  parsed <- parse_args(argv)

  api_key <- trimws(value_or_empty(env, "EVAGENE_API_KEY"))
  if (!nzchar(api_key)) {
    stop_config("EVAGENE_API_KEY environment variable is required.")
  }

  require_uuid(parsed$pedigree_id, "pedigree-id")

  base_url <- trimws(value_or_empty(env, "EVAGENE_BASE_URL"))
  if (!nzchar(base_url)) {
    base_url <- DEFAULT_BASE_URL
  }

  list(
    base_url = base_url,
    api_key = api_key,
    pedigree_id = parsed$pedigree_id,
    output_path = parsed$output_path,
    deidentify = parsed$deidentify,
    label_style = parsed$label_style,
    width = parsed$width,
    height = parsed$height
  )
}

parse_args <- function(argv) {
  pedigree_id <- NULL
  output_path <- NULL
  deidentify <- FALSE
  label_style <- DEFAULT_LABEL_STYLE
  width <- NULL
  height <- NULL

  index <- 1L
  while (index <= length(argv)) {
    token <- argv[[index]]
    if (token == "--output") {
      output_path <- require_value_for(argv, index, "--output")
      index <- index + 2L
    } else if (token == "--deidentify") {
      deidentify <- TRUE
      index <- index + 1L
    } else if (token == "--label-style") {
      label_style <- require_value_for(argv, index, "--label-style")
      index <- index + 2L
    } else if (token == "--width") {
      width <- parse_positive_int(
        require_value_for(argv, index, "--width"), "--width"
      )
      index <- index + 2L
    } else if (token == "--height") {
      height <- parse_positive_int(
        require_value_for(argv, index, "--height"), "--height"
      )
      index <- index + 2L
    } else if (!startsWith(token, "--") && is.null(pedigree_id)) {
      pedigree_id <- token
      index <- index + 1L
    } else {
      stop_config(sprintf("Unexpected argument: %s", token))
    }
  }

  if (is.null(pedigree_id)) {
    stop_config("pedigree-id is required")
  }
  if (is.null(output_path)) {
    stop_config("--output is required")
  }
  if (!label_style %in% LABEL_STYLES) {
    stop_config(sprintf(
      "--label-style must be one of %s, got: %s",
      paste(LABEL_STYLES, collapse = ", "), label_style
    ))
  }

  list(
    pedigree_id = pedigree_id,
    output_path = output_path,
    deidentify = deidentify,
    label_style = label_style,
    width = width,
    height = height
  )
}

require_value_for <- function(argv, index, label) {
  if (index == length(argv)) {
    stop_config(sprintf("%s requires a value", label))
  }
  argv[[index + 1L]]
}

require_uuid <- function(value, label) {
  if (!grepl(UUID_PATTERN, value, ignore.case = TRUE)) {
    stop_config(sprintf("%s must be a UUID, got: %s", label, value))
  }
}

parse_positive_int <- function(raw, label) {
  if (!grepl("^[0-9]+$", raw)) {
    stop_config(sprintf("%s must be a positive integer, got: %s", label, raw))
  }
  value <- as.integer(raw)
  if (is.na(value) || value <= 0L) {
    stop_config(sprintf("%s must be a positive integer, got: %s", label, raw))
  }
  value
}

value_or_empty <- function(env, key) {
  value <- env[[key]]
  if (is.null(value) || is.na(value)) "" else value
}
