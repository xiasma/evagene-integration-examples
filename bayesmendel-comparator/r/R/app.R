# Composition root -- wires config, api client, model registry,
# comparison builder, and presenter.

EXIT_OK <- 0L
EXIT_USAGE <- 64L
EXIT_UNAVAILABLE <- 69L
EXIT_SCHEMA <- 70L

#' Run the BayesMendel comparator pipeline end-to-end.
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
    payloads <- fetch_all_models(gateway, config)
    comparison <- build_comparison(payloads)
    present <- presenter_for(config$format)
    present(comparison, out_sink)
    EXIT_OK
  },
    config_error = function(e) handle_error(e, err_sink, EXIT_USAGE),
    api_error = function(e) handle_error(e, err_sink, EXIT_UNAVAILABLE),
    response_schema_error = function(e) handle_error(e, err_sink, EXIT_SCHEMA)
  )
}

fetch_all_models <- function(gateway, config) {
  models <- bayesmendel_models()
  payloads <- lapply(models, function(model) {
    calculate_risk(
      gateway, config$base_url, config$api_key,
      config$pedigree_id, model, config$counselee_id
    )
  })
  names(payloads) <- models
  payloads
}

handle_error <- function(condition, err_sink, code) {
  cat(sprintf("error: %s\n", conditionMessage(condition)), file = err_sink)
  code
}
