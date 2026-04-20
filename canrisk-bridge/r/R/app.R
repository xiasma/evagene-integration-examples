# Composition root -- wires config, canrisk client, output sink.

EXIT_OK <- 0L
EXIT_USAGE <- 64L
EXIT_UNAVAILABLE <- 69L
EXIT_FORMAT <- 70L

#' Run the CanRisk bridge pipeline end-to-end.
#'
#' @param argv Character vector of CLI args (without program name).
#' @param env Named list of environment variables.
#' @param out_sink Writable connection for normal output.
#' @param err_sink Writable connection for error messages.
#' @param gateway Optional HTTP gateway function; defaults to `make_httr2_gateway()`.
#' @param browser Optional browser-launcher function; defaults to `utils::browseURL`.
#' @return Integer exit code (see EXIT_* constants).
app_run <- function(argv, env,
                    out_sink = stdout(),
                    err_sink = stderr(),
                    gateway = NULL,
                    browser = NULL) {
  if (is.null(gateway)) {
    gateway <- make_httr2_gateway()
  }
  if (is.null(browser)) {
    browser <- utils::browseURL
  }

  tryCatch({
    config <- load_config(argv, env)
    payload <- fetch_canrisk(
      gateway, config$base_url, config$api_key, config$pedigree_id
    )
    saved_path <- save_canrisk(config$output_dir, config$pedigree_id, payload)
    cat(saved_path, "\n", file = out_sink, sep = "")
    if (isTRUE(config$open_browser)) {
      open_upload_page(browser)
    }
    EXIT_OK
  },
    config_error = function(e) handle_error(e, err_sink, EXIT_USAGE),
    api_error = function(e) handle_error(e, err_sink, EXIT_UNAVAILABLE),
    canrisk_format_error = function(e) handle_error(e, err_sink, EXIT_FORMAT)
  )
}

handle_error <- function(condition, err_sink, code) {
  cat(sprintf("error: %s\n", conditionMessage(condition)), file = err_sink)
  code
}
