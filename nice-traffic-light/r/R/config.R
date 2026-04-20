# Immutable configuration from CLI args + environment.

DEFAULT_BASE_URL <- "https://evagene.net"
UUID_PATTERN <- "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"

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
#' @param env Named list (not a character vector) of environment variables;
#'   callers coming from `Sys.getenv()` should use `as.list(Sys.getenv())`.
#' @return A named list with fields base_url, api_key, pedigree_id, counselee_id.
load_config <- function(argv, env) {
  parsed <- parse_args(argv)

  api_key <- trimws(value_or_empty(env, "EVAGENE_API_KEY"))
  if (!nzchar(api_key)) {
    stop_config("EVAGENE_API_KEY environment variable is required.")
  }

  require_uuid(parsed$pedigree_id, "pedigree-id")
  if (!is.null(parsed$counselee_id)) {
    require_uuid(parsed$counselee_id, "--counselee")
  }

  base_url <- trimws(value_or_empty(env, "EVAGENE_BASE_URL"))
  if (!nzchar(base_url)) {
    base_url <- DEFAULT_BASE_URL
  }

  list(
    base_url = base_url,
    api_key = api_key,
    pedigree_id = parsed$pedigree_id,
    counselee_id = parsed$counselee_id
  )
}

parse_args <- function(argv) {
  pedigree_id <- NULL
  counselee_id <- NULL
  index <- 1L
  while (index <= length(argv)) {
    token <- argv[[index]]
    if (token == "--counselee") {
      if (index == length(argv)) {
        stop_config("--counselee requires a value")
      }
      counselee_id <- argv[[index + 1L]]
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
  list(pedigree_id = pedigree_id, counselee_id = counselee_id)
}

require_uuid <- function(value, label) {
  if (!grepl(UUID_PATTERN, value, ignore.case = TRUE)) {
    stop_config(sprintf("%s must be a UUID, got: %s", label, value))
  }
}

value_or_empty <- function(env, key) {
  value <- env[[key]]
  if (is.null(value) || is.na(value)) "" else value
}
