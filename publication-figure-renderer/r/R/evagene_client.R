# Thin client for the two Evagene endpoints this demo needs.

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

#' Fetch the SVG export of a pedigree.
#'
#' @param gateway A gateway function (see `make_httr2_gateway()`).
#' @param base_url Evagene base URL (trailing slash optional).
#' @param api_key Value for the `X-API-Key` header.
#' @param pedigree_id UUID string.
#' @return The raw SVG document as a single character string.
fetch_pedigree_svg <- function(gateway, base_url, api_key, pedigree_id) {
  url <- sprintf(
    "%s/api/pedigrees/%s/export.svg", sub("/$", "", base_url), pedigree_id
  )
  response <- gateway(list(
    method = "GET",
    url = url,
    headers = c("X-API-Key" = api_key, "Accept" = "image/svg+xml")
  ))
  require_ok(response, url)
  response$body_text
}

#' Fetch pedigree detail (metadata + resolved individuals/relationships/eggs).
#'
#' @param gateway A gateway function (see `make_httr2_gateway()`).
#' @param base_url Evagene base URL (trailing slash optional).
#' @param api_key Value for the `X-API-Key` header.
#' @param pedigree_id UUID string.
#' @return A named list parsed from the JSON response.
fetch_pedigree_detail <- function(gateway, base_url, api_key, pedigree_id) {
  url <- sprintf(
    "%s/api/pedigrees/%s", sub("/$", "", base_url), pedigree_id
  )
  response <- gateway(list(
    method = "GET",
    url = url,
    headers = c("X-API-Key" = api_key, "Accept" = "application/json")
  ))
  require_ok(response, url)

  parsed <- tryCatch(
    jsonlite::fromJSON(response$body_text, simplifyVector = FALSE),
    error = function(e) {
      stop_api(sprintf("Evagene API returned invalid JSON: %s", conditionMessage(e)))
    }
  )
  if (!is.list(parsed) || is.null(names(parsed))) {
    stop_api("Evagene API returned non-object JSON for pedigree detail")
  }
  parsed
}

require_ok <- function(response, url) {
  if (response$status < HTTP_OK_LOWER || response$status >= HTTP_OK_UPPER) {
    stop_api(sprintf("Evagene API returned HTTP %d for %s", response$status, url))
  }
}
