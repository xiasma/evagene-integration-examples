# Immutable configuration from environment variables.

DEFAULT_BASE_URL <- "https://evagene.net"

#' Raise a config_error condition.
#' @noRd
stop_config <- function(message) {
  stop(structure(
    list(message = message, call = sys.call(-1)),
    class = c("config_error", "error", "condition")
  ))
}

#' Load configuration from environment variables.
#'
#' @param env Named list (not a character vector) of environment variables;
#'   callers coming from `Sys.getenv()` should use `as.list(Sys.getenv())`.
#' @return A named list with fields base_url, api_key.
load_config <- function(env) {
  api_key <- trimws(value_or_empty(env, "EVAGENE_API_KEY"))
  if (!nzchar(api_key)) {
    stop_config(paste(
      "EVAGENE_API_KEY environment variable is required.",
      "See ../README.md for how to mint a key."
    ))
  }
  base_url <- trimws(value_or_empty(env, "EVAGENE_BASE_URL"))
  if (!nzchar(base_url)) {
    base_url <- DEFAULT_BASE_URL
  }
  list(base_url = sub("/$", "", base_url), api_key = api_key)
}

value_or_empty <- function(env, key) {
  value <- env[[key]]
  if (is.null(value) || is.na(value)) "" else value
}
