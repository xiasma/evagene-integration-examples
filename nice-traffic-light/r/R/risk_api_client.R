# Call Evagene's /risk/calculate endpoint for the NICE model.

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

#' Call the Evagene risk/calculate endpoint with model=NICE.
#'
#' @param gateway A gateway function built by e.g. `make_httr2_gateway()`.
#' @param base_url Evagene base URL (trailing slash optional).
#' @param api_key Value for the `X-API-Key` header.
#' @param pedigree_id UUID string.
#' @param counselee_id Optional UUID string.
#' @return A named list parsed from the response JSON.
calculate_nice <- function(gateway, base_url, api_key, pedigree_id, counselee_id = NULL) {
  url <- sprintf("%s/api/pedigrees/%s/risk/calculate", sub("/$", "", base_url), pedigree_id)
  body <- list(model = "NICE")
  if (!is.null(counselee_id)) {
    body$counselee_id <- counselee_id
  }

  response <- gateway(list(
    url = url,
    headers = c("X-API-Key" = api_key, "Accept" = "application/json"),
    body_json = jsonlite::toJSON(body, auto_unbox = TRUE)
  ))

  if (response$status < HTTP_OK_LOWER || response$status >= HTTP_OK_UPPER) {
    stop_api(sprintf("Evagene API returned HTTP %d for %s", response$status, url))
  }

  parsed <- tryCatch(
    jsonlite::fromJSON(response$json_body, simplifyVector = FALSE),
    error = function(e) {
      stop_api(sprintf("Evagene API returned invalid JSON: %s", conditionMessage(e)))
    }
  )
  if (!is.list(parsed) || is.null(names(parsed))) {
    stop_api("Evagene API returned non-object JSON")
  }
  parsed
}
