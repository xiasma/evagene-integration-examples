# Immutable configuration from CLI args + environment.

DEFAULT_BASE_URL <- "https://evagene.net"
UUID_PATTERN <- "^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
VALID_PRECISIONS <- c("year", "five-year", "decade")

stop_config <- function(message) {
  stop(structure(
    list(message = message, call = sys.call(-1)),
    class = c("config_error", "error", "condition")
  ))
}

#' Load configuration from CLI args + environment.
#'
#' @param argv Character vector of CLI arguments (without program name).
#' @param env Named list of environment variables (use `as.list(Sys.getenv())`).
#' @return A named list: base_url, api_key, pedigree_id, output_path,
#'   as_new_pedigree, age_precision, keep_sex.
load_config <- function(argv, env) {
  parsed <- parse_args(argv)

  api_key <- trimws(value_or_empty(env, "EVAGENE_API_KEY"))
  if (!nzchar(api_key)) {
    stop_config("EVAGENE_API_KEY environment variable is required.")
  }

  require_uuid(parsed$pedigree_id, "pedigree-id")

  if (!is.null(parsed$output_path) && parsed$as_new_pedigree) {
    stop_config("--output and --as-new-pedigree are mutually exclusive.")
  }

  base_url <- trimws(value_or_empty(env, "EVAGENE_BASE_URL"))
  if (!nzchar(base_url)) {
    base_url <- DEFAULT_BASE_URL
  }

  list(
    base_url = base_url,
    api_key = api_key,
    pedigree_id = parsed$pedigree_id,
    output_path = parsed$output_path,
    as_new_pedigree = parsed$as_new_pedigree,
    age_precision = parsed$age_precision,
    keep_sex = parsed$keep_sex
  )
}

parse_args <- function(argv) {
  pedigree_id <- NULL
  output_path <- NULL
  as_new_pedigree <- FALSE
  age_precision <- "year"
  keep_sex <- TRUE

  index <- 1L
  while (index <= length(argv)) {
    token <- argv[[index]]
    if (token == "--output") {
      if (index == length(argv)) {
        stop_config("--output requires a value")
      }
      output_path <- argv[[index + 1L]]
      index <- index + 2L
    } else if (token == "--as-new-pedigree") {
      as_new_pedigree <- TRUE
      index <- index + 1L
    } else if (token == "--age-precision") {
      if (index == length(argv)) {
        stop_config("--age-precision requires a value")
      }
      age_precision <- argv[[index + 1L]]
      if (!age_precision %in% VALID_PRECISIONS) {
        stop_config(sprintf(
          "--age-precision must be one of: %s",
          paste(VALID_PRECISIONS, collapse = ", ")
        ))
      }
      index <- index + 2L
    } else if (token == "--keep-sex") {
      keep_sex <- TRUE
      index <- index + 1L
    } else if (token == "--no-keep-sex") {
      keep_sex <- FALSE
      index <- index + 1L
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
  list(
    pedigree_id = pedigree_id,
    output_path = output_path,
    as_new_pedigree = as_new_pedigree,
    age_precision = age_precision,
    keep_sex = keep_sex
  )
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
