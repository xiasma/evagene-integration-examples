# Narrow Evagene REST client covering only the calls this demo needs.
#
# Each function wraps one endpoint.  Non-2xx responses and non-object
# JSON surface as api_error conditions with a diagnostic that names
# the URL — a reader debugging a 403 should not have to guess which
# call it came from.  The full API surface lives in the OpenAPI spec
# at https://evagene.net/docs.

HTTP_OK_LOWER <- 200L
HTTP_OK_UPPER <- 300L

#' Raise an api_error condition.
#' @noRd
stop_api <- function(message) {
  stop(structure(
    list(message = message, call = sys.call(-1)),
    class = c("api_error", "error", "condition")
  ))
}

# --- Helpers --------------------------------------------------------------

auth_headers <- function(api_key) {
  c(
    "X-API-Key" = api_key,
    "Accept" = "application/json"
  )
}

perform_json <- function(gateway, method, url, api_key,
                         body = NULL, params = NULL) {
  request <- list(
    method = method,
    url = url,
    headers = auth_headers(api_key),
    params = params
  )
  if (!is.null(body)) {
    request$body_json <- jsonlite::toJSON(body, auto_unbox = TRUE, null = "null")
  }
  response <- gateway(request)
  if (response$status < HTTP_OK_LOWER || response$status >= HTTP_OK_UPPER) {
    stop_api(sprintf(
      "Evagene API returned HTTP %d for %s: %s",
      response$status, url, truncate_text(response$json_body %||% "")
    ))
  }
  response
}

perform_no_content <- function(gateway, method, url, api_key, body = NULL) {
  perform_json(gateway, method, url, api_key, body = body)
  invisible(NULL)
}

parse_object <- function(response, url) {
  parsed <- tryCatch(
    jsonlite::fromJSON(response$json_body, simplifyVector = FALSE),
    error = function(e) {
      stop_api(sprintf("Evagene API returned invalid JSON for %s: %s", url, conditionMessage(e)))
    }
  )
  if (!is.list(parsed) || is.null(names(parsed))) {
    stop_api(sprintf("Evagene API returned non-object JSON for %s", url))
  }
  parsed
}

require_id <- function(payload, where) {
  identifier <- payload$id
  if (!is.character(identifier) || length(identifier) != 1L || !nzchar(identifier)) {
    stop_api(sprintf("%s lacks a string 'id' field", where))
  }
  identifier
}

truncate_text <- function(text, limit = 200L) {
  if (nchar(text) <= limit) text else paste0(substr(text, 1L, limit - 3L), "...")
}

`%||%` <- function(a, b) if (is.null(a)) b else a

# --- Pedigrees ------------------------------------------------------------

#' Create a scratch pedigree and return its UUID.
create_pedigree <- function(gateway, base_url, api_key, display_name) {
  url <- sprintf("%s/api/pedigrees", trim_trailing_slash(base_url))
  response <- perform_json(
    gateway, "POST", url, api_key,
    body = list(display_name = display_name)
  )
  require_id(parse_object(response, url), where = "create_pedigree response")
}

delete_pedigree <- function(gateway, base_url, api_key, pedigree_id) {
  url <- sprintf("%s/api/pedigrees/%s", trim_trailing_slash(base_url), pedigree_id)
  perform_no_content(gateway, "DELETE", url, api_key)
}

add_individual_to_pedigree <- function(gateway, base_url, api_key,
                                       pedigree_id, individual_id) {
  url <- sprintf(
    "%s/api/pedigrees/%s/individuals/%s",
    trim_trailing_slash(base_url), pedigree_id, individual_id
  )
  perform_no_content(gateway, "POST", url, api_key)
}

# --- Individuals ----------------------------------------------------------

#' Create an individual and return their UUID.
create_individual <- function(gateway, base_url, api_key,
                              display_name, biological_sex) {
  url <- sprintf("%s/api/individuals", trim_trailing_slash(base_url))
  body <- list(display_name = display_name)
  if (!is.null(biological_sex) && biological_sex != SEX_UNKNOWN) {
    body$biological_sex <- biological_sex
  }
  response <- perform_json(gateway, "POST", url, api_key, body = body)
  require_id(parse_object(response, url), where = "create_individual response")
}

delete_individual <- function(gateway, base_url, api_key, individual_id) {
  url <- sprintf("%s/api/individuals/%s", trim_trailing_slash(base_url), individual_id)
  perform_no_content(gateway, "DELETE", url, api_key)
}

#' Upload a raw 23andMe genotype TSV to the named individual.
#'
#' The target individual is passed as the `individual_id` query
#' parameter (not in the JSON body) -- verified against the Evagene
#' API at the time of writing.
import_23andme_raw <- function(gateway, base_url, api_key,
                               pedigree_id, individual_id, tsv) {
  url <- sprintf(
    "%s/api/pedigrees/%s/import/23andme-raw",
    trim_trailing_slash(base_url), pedigree_id
  )
  perform_json(
    gateway, "POST", url, api_key,
    body = list(content = tsv),
    params = c("individual_id" = individual_id)
  )
  invisible(NULL)
}

#' Look up an ancestry UUID by its `population_key`.
find_ancestry_id_by_population_key <- function(gateway, base_url, api_key, population_key) {
  url <- sprintf("%s/api/ancestries", trim_trailing_slash(base_url))
  response <- perform_json(gateway, "GET", url, api_key)
  parsed <- tryCatch(
    jsonlite::fromJSON(response$json_body, simplifyVector = FALSE),
    error = function(e) {
      stop_api(sprintf("Evagene API returned invalid JSON for %s: %s", url, conditionMessage(e)))
    }
  )
  if (!is.list(parsed)) {
    stop_api(sprintf("Expected a list from %s", url))
  }
  for (entry in parsed) {
    if (is.list(entry) && identical(entry$population_key, population_key)) {
      if (is.character(entry$id) && length(entry$id) == 1L) {
        return(entry$id)
      }
    }
  }
  NULL
}

add_ancestry_to_individual <- function(gateway, base_url, api_key,
                                       individual_id, ancestry_id,
                                       proportion = 1.0) {
  url <- sprintf(
    "%s/api/individuals/%s/ancestries",
    trim_trailing_slash(base_url), individual_id
  )
  perform_json(
    gateway, "POST", url, api_key,
    body = list(ancestry_id = ancestry_id, proportion = proportion)
  )
  invisible(NULL)
}

get_population_risks <- function(gateway, base_url, api_key, individual_id) {
  url <- sprintf(
    "%s/api/individuals/%s/population-risks",
    trim_trailing_slash(base_url), individual_id
  )
  response <- perform_json(gateway, "GET", url, api_key)
  parse_object(response, url)
}

trim_trailing_slash <- function(url) sub("/$", "", url)
