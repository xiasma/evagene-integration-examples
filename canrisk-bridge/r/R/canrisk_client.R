# Call Evagene's /risk/canrisk endpoint and return the ##CanRisk 2.0 body.

CANRISK_HEADER <- "##CanRisk 2.0"
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

#' Raise a canrisk_format_error condition.
#' @noRd
stop_format <- function(message) {
  stop(structure(
    list(message = message, call = sys.call(-1)),
    class = c("canrisk_format_error", "error", "condition")
  ))
}

#' Fetch a pedigree as a ##CanRisk 2.0 file.
#'
#' @param gateway A gateway function built by e.g. `make_httr2_gateway()`.
#' @param base_url Evagene base URL (trailing slash optional).
#' @param api_key Value for the `X-API-Key` header.
#' @param pedigree_id UUID string.
#' @return The response body as a single character string beginning with
#'   `##CanRisk 2.0`.
fetch_canrisk <- function(gateway, base_url, api_key, pedigree_id) {
  url <- sprintf("%s/api/pedigrees/%s/risk/canrisk", sub("/$", "", base_url), pedigree_id)

  response <- gateway(list(
    url = url,
    headers = c("X-API-Key" = api_key, "Accept" = "text/tab-separated-values")
  ))

  if (response$status < HTTP_OK_LOWER || response$status >= HTTP_OK_UPPER) {
    stop_api(sprintf("Evagene API returned HTTP %d for %s", response$status, url))
  }

  if (!startsWith(response$body, CANRISK_HEADER)) {
    stop_format(sprintf(
      paste0(
        "Response body does not begin with '%s'; ",
        "check the pedigree ID and that your key has the 'analyze' scope."
      ),
      CANRISK_HEADER
    ))
  }
  response$body
}
