# Composition root -- wires config, api client, classifier, mapper, presenter.

EXIT_GREEN <- 0L
EXIT_AMBER <- 1L
EXIT_RED <- 2L
EXIT_USAGE <- 64L
EXIT_UNAVAILABLE <- 69L
EXIT_SCHEMA <- 70L

#' Run the NICE traffic-light pipeline end-to-end.
#'
#' @param argv Character vector of CLI args (without program name).
#' @param env Named list of environment variables.
#' @param out_sink Writable connection for normal output.
#' @param err_sink Writable connection for error messages.
#' @param gateway Optional HTTP gateway function; defaults to `make_httr2_gateway()`.
#' @return Integer exit code (see EXIT_* constants).
app_run <- function(argv, env,
                    out_sink = stdout(),
                    err_sink = stderr(),
                    gateway = NULL) {
  if (is.null(gateway)) {
    gateway <- make_httr2_gateway()
  }

  tryCatch({
    config <- load_config(argv, env)
    payload <- calculate_nice(
      gateway, config$base_url, config$api_key,
      config$pedigree_id, config$counselee_id
    )
    outcome <- classify_nice_response(payload)
    report <- to_traffic_light(outcome)
    present(report, out_sink)
    exit_code_for(report$colour)
  },
    config_error = function(e) handle_error(e, err_sink, EXIT_USAGE),
    api_error = function(e) handle_error(e, err_sink, EXIT_UNAVAILABLE),
    response_schema_error = function(e) handle_error(e, err_sink, EXIT_SCHEMA)
  )
}

handle_error <- function(condition, err_sink, code) {
  cat(sprintf("error: %s\n", conditionMessage(condition)), file = err_sink)
  code
}

exit_code_for <- function(colour) {
  switch(colour,
    GREEN = EXIT_GREEN,
    AMBER = EXIT_AMBER,
    RED = EXIT_RED,
    stop(sprintf("Unknown colour: %s", colour))
  )
}
