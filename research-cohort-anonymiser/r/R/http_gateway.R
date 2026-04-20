# HTTP gateway abstraction.
#
# A gateway is a plain function:
#
#   gateway(request) -> list(status = integer, json_body = character)
#
# where request is a named list with:
#   - method   ("GET", "POST", "PATCH", "DELETE")
#   - url      (character)
#   - headers  (named character vector)
#   - body_json (character, or NULL for no body)
#
# Tests substitute their own function with no ceremony.

#' Build an httr2-backed HTTP gateway.
#'
#' @param timeout_seconds Request timeout in seconds.
#' @return A function accepting a request list and returning a response list.
make_httr2_gateway <- function(timeout_seconds = 10) {
  force(timeout_seconds)
  function(request) {
    req <- httr2::request(request$url)
    req <- httr2::req_method(req, request$method)
    req <- httr2::req_headers(req, !!!as.list(request$headers))
    if (!is.null(request$body_json)) {
      req <- httr2::req_body_raw(req, request$body_json, type = "application/json")
    }
    req <- httr2::req_timeout(req, timeout_seconds)
    req <- httr2::req_error(req, is_error = function(resp) FALSE)

    resp <- httr2::req_perform(req)
    status <- httr2::resp_status(resp)
    body <- tryCatch(httr2::resp_body_string(resp), error = function(e) "")
    list(status = status, json_body = body)
  }
}
