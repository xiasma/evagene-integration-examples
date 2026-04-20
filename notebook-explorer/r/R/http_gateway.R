# HTTP gateway abstraction.
#
# A "gateway" here is a function:
#
#   gateway(request) -> list(status = integer, json_body = character)
#
# where `request` is a named list with fields `method`, `url`, `headers`
# (named character vector) and (optional) `body_json` (raw JSON string).
# Tests substitute their own function with no ceremony.

#' Build an `httr2`-backed HTTP gateway that follows redirects and returns
#' status + body text.  A 429 response is retried after a pause — callers
#' should not special-case rate limits themselves.
#'
#' @param timeout_seconds Request timeout in seconds.
#' @param rate_limit_wait_seconds Pause between retries when the server
#'   returns HTTP 429.
#' @param rate_limit_max_retries Cap on retries before giving up.
#' @param sleeper Injectable sleep function; defaults to `Sys.sleep`.
#' @return A function accepting a request list and returning a response list.
make_httr2_gateway <- function(timeout_seconds = 30,
                               rate_limit_wait_seconds = 5,
                               rate_limit_max_retries = 12,
                               sleeper = Sys.sleep) {
  force(timeout_seconds)
  force(rate_limit_wait_seconds)
  force(rate_limit_max_retries)
  force(sleeper)
  function(request) {
    method <- toupper(request$method %||% "GET")
    for (attempt in seq_len(rate_limit_max_retries + 1L)) {
      req <- httr2::request(request$url)
      req <- httr2::req_method(req, method)
      req <- httr2::req_headers(req, !!!as.list(request$headers))
      if (!is.null(request$body_json)) {
        req <- httr2::req_body_raw(req, request$body_json, type = "application/json")
      }
      req <- httr2::req_timeout(req, timeout_seconds)
      req <- httr2::req_error(req, is_error = function(resp) FALSE)

      resp <- httr2::req_perform(req)
      status <- httr2::resp_status(resp)
      if (status == 429L) {
        sleeper(rate_limit_wait_seconds)
        next
      }
      body_string <- tryCatch(
        httr2::resp_body_string(resp),
        error = function(e) ""
      )
      return(list(status = status, body_string = body_string))
    }
    stop(structure(
      list(message = sprintf(
        "Evagene API still rate-limited after %d retries for %s %s",
        rate_limit_max_retries, method, request$url
      ), call = sys.call(-1)),
      class = c("api_error", "error", "condition")
    ))
  }
}

`%||%` <- function(a, b) if (is.null(a)) b else a
