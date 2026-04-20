# Immutable configuration from CLI args + environment.

DEFAULT_BASE_URL <- "https://evagene.net"
AUTO_ANCESTRY <- "auto"
SUPPORTED_FORMATS <- c("table", "csv", "json")

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
#' @return A named list with fields base_url, api_key, partner_a_file,
#'   partner_b_file, ancestry_a, ancestry_b, output, cleanup.
load_config <- function(argv, env) {
  parsed <- parse_args(argv)

  api_key <- trimws(value_or_empty(env, "EVAGENE_API_KEY"))
  if (!nzchar(api_key)) {
    stop_config(paste0(
      "EVAGENE_API_KEY environment variable is required. ",
      "Create a key at https://evagene.net (Account settings -> API keys)."
    ))
  }

  base_url <- trimws(value_or_empty(env, "EVAGENE_BASE_URL"))
  if (!nzchar(base_url)) {
    base_url <- DEFAULT_BASE_URL
  }

  list(
    base_url = base_url,
    api_key = api_key,
    partner_a_file = parsed$partner_a_file,
    partner_b_file = parsed$partner_b_file,
    ancestry_a = parsed$ancestry_a,
    ancestry_b = parsed$ancestry_b,
    output = parsed$output,
    cleanup = parsed$cleanup
  )
}

parse_args <- function(argv) {
  state <- list(
    partner_a_file = NULL,
    partner_b_file = NULL,
    ancestry_a = AUTO_ANCESTRY,
    ancestry_b = AUTO_ANCESTRY,
    output = "table",
    cleanup = TRUE
  )
  index <- 1L
  while (index <= length(argv)) {
    token <- argv[[index]]
    if (token == "--partner-a") {
      state$partner_a_file <- require_value_for(argv, index, "--partner-a")
      index <- index + 2L
    } else if (token == "--partner-b") {
      state$partner_b_file <- require_value_for(argv, index, "--partner-b")
      index <- index + 2L
    } else if (token == "--ancestry-a") {
      state$ancestry_a <- require_value_for(argv, index, "--ancestry-a")
      index <- index + 2L
    } else if (token == "--ancestry-b") {
      state$ancestry_b <- require_value_for(argv, index, "--ancestry-b")
      index <- index + 2L
    } else if (token == "--output") {
      state$output <- require_value_for(argv, index, "--output")
      index <- index + 2L
    } else if (token == "--cleanup") {
      state$cleanup <- TRUE
      index <- index + 1L
    } else if (token == "--no-cleanup") {
      state$cleanup <- FALSE
      index <- index + 1L
    } else {
      stop_config(sprintf("Unexpected argument: %s", token))
    }
  }
  if (is.null(state$partner_a_file)) {
    stop_config("--partner-a is required")
  }
  if (is.null(state$partner_b_file)) {
    stop_config("--partner-b is required")
  }
  if (!state$output %in% SUPPORTED_FORMATS) {
    stop_config(sprintf(
      "--output must be one of %s, got: %s",
      paste(SUPPORTED_FORMATS, collapse = ", "), state$output
    ))
  }
  state
}

require_value_for <- function(argv, index, label) {
  if (index == length(argv)) {
    stop_config(sprintf("%s requires a value", label))
  }
  argv[[index + 1L]]
}

value_or_empty <- function(env, key) {
  value <- env[[key]]
  if (is.null(value) || is.na(value)) "" else value
}
