# Composition root -- wires config, evagene_client, orchestrator, presenters.

EXIT_OK <- 0L
EXIT_USAGE <- 64L
EXIT_UNAVAILABLE <- 69L
EXIT_SCHEMA <- 70L

#' Run the couple-carrier-risk pipeline end-to-end.
#'
#' @param argv Character vector of CLI args (without program name).
#' @param env Named list of environment variables.
#' @param out_sink Writable connection for normal output.  Named
#'   `out_sink` (not `stdout`) to avoid recursive-promise issues when
#'   callers default it from `stdout()`.
#' @param err_sink Writable connection for error messages.
#' @param client Optional Evagene client list (see `make_evagene_client()`);
#'   tests pass a fake, production defaults to the httr2-backed client.
#' @return Integer exit code (see EXIT_* constants).
app_run <- function(argv, env,
                    out_sink = stdout(),
                    err_sink = stderr(),
                    client = NULL) {
  if (is.null(client)) {
    gateway <- make_httr2_gateway()
    client_cfg <- tryCatch(load_config(argv, env),
      config_error = function(e) e
    )
    if (inherits(client_cfg, "config_error")) {
      return(handle_error(client_cfg, err_sink, EXIT_USAGE))
    }
    client <- make_evagene_client(gateway, client_cfg$base_url, client_cfg$api_key)
    return(run_with_client(client_cfg, client, out_sink, err_sink))
  }

  config <- tryCatch(load_config(argv, env),
    config_error = function(e) e
  )
  if (inherits(config, "config_error")) {
    return(handle_error(config, err_sink, EXIT_USAGE))
  }
  run_with_client(config, client, out_sink, err_sink)
}

run_with_client <- function(config, client, out_sink, err_sink) {
  tryCatch({
    run_couple_screening(config, client, out_sink)
    EXIT_OK
  },
    genome_file_error = function(e) handle_error(e, err_sink, EXIT_USAGE),
    ancestry_not_found_error = function(e) handle_error(e, err_sink, EXIT_USAGE),
    api_error = function(e) handle_error(e, err_sink, EXIT_UNAVAILABLE),
    response_schema_error = function(e) handle_error(e, err_sink, EXIT_SCHEMA)
  )
}

handle_error <- function(condition, err_sink, code) {
  cat(sprintf("error: %s\n", conditionMessage(condition)), file = err_sink)
  code
}
