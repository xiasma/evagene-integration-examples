# Call Evagene's /risk/calculate endpoint.  The model name is data.

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

#' Run a single Evagene risk calculation.
#'
#' @param gateway     A gateway function (see `make_httr2_gateway()`).
#' @param base_url    Evagene base URL (trailing slash optional).
#' @param api_key     Value for the `X-API-Key` header.
#' @param pedigree_id UUID string.
#' @param model       Model name (e.g. "BRCAPRO", "MMRpro", "PancPRO").
#' @param counselee_id Optional UUID string.
#' @return A named list parsed from the response JSON.
calculate_risk <- function(gateway, base_url, api_key,
                           pedigree_id, model, counselee_id = NULL) {
  url <- sprintf(
    "%s/api/pedigrees/%s/risk/calculate",
    sub("/$", "", base_url), pedigree_id
  )
  body <- list(model = model)
  if (!is.null(counselee_id)) {
    body$counselee_id <- counselee_id
  }

  response <- gateway(list(
    url = url,
    headers = c("X-API-Key" = api_key, "Accept" = "application/json"),
    body_json = jsonlite::toJSON(body, auto_unbox = TRUE)
  ))

  if (response$status < HTTP_OK_LOWER || response$status >= HTTP_OK_UPPER) {
    stop_api(sprintf(
      "Evagene API returned HTTP %d for model %s", response$status, model
    ))
  }

  parsed <- tryCatch(
    jsonlite::fromJSON(response$json_body, simplifyVector = FALSE),
    error = function(e) {
      stop_api(sprintf(
        "Evagene API returned invalid JSON for model %s: %s",
        model, conditionMessage(e)
      ))
    }
  )
  if (!is.list(parsed) || is.null(names(parsed))) {
    stop_api(sprintf("Evagene API returned non-object JSON for model %s", model))
  }
  parsed
}
