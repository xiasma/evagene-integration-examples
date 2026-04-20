# HTTP gateway abstraction.
#
# A "gateway" here is a plain function:
#
#   gateway(request) -> list(status = integer, body = character)
#
# where `request` is a named list with fields `url` and `headers`
# (named character vector).  Tests substitute their own function
# with no ceremony.

#' Build an `httr2`-backed HTTP GET gateway.
#'
#' @param timeout_seconds Request timeout in seconds.
#' @return A function accepting a request list and returning a response list.
make_httr2_gateway <- function(timeout_seconds = 10) {
  force(timeout_seconds)
  function(request) {
    req <- httr2::request(request$url)
    req <- httr2::req_method(req, "GET")
    req <- httr2::req_headers(req, !!!as.list(request$headers))
    req <- httr2::req_timeout(req, timeout_seconds)
    req <- httr2::req_error(req, is_error = function(resp) FALSE)

    resp <- httr2::req_perform(req)
    list(
      status = httr2::resp_status(resp),
      body = httr2::resp_body_string(resp)
    )
  }
}
