# Composition root -- wires config, client, anonymiser, presenter, writer.

EXIT_OK <- 0L
EXIT_USAGE <- 64L
EXIT_UNAVAILABLE <- 69L
EXIT_SCHEMA <- 70L

#' Run the anonymiser pipeline end-to-end.
#'
#' @param argv Character vector of CLI args (without program name).
#' @param env Named list of environment variables.
#' @param out_sink Writable connection for normal output.
#' @param err_sink Writable connection for error messages.
#' @param client Optional Evagene client; defaults to the httr2-backed one.
#' @return Integer exit code (see EXIT_* constants).
app_run <- function(argv, env,
                    out_sink = stdout(),
                    err_sink = stderr(),
                    client = NULL) {
  tryCatch({
    config <- load_config(argv, env)
    if (is.null(client)) {
      gateway <- make_httr2_gateway()
      client <- make_evagene_client(gateway, config$base_url, config$api_key)
    }

    source_pedigree <- client$get_pedigree_detail(config$pedigree_id)
    labels <- assign_generation_labels(source_pedigree)
    rules <- list(age_precision = config$age_precision, keep_sex = config$keep_sex)
    anonymised <- anonymise_pedigree(source_pedigree, labels, rules)
    estimate <- estimate_k_anonymity(anonymised)
    rendered <- render_json(anonymised, estimate)

    sink <- sink_for(config, client, out_sink, err_sink)
    sink(rendered, anonymised)
    EXIT_OK
  },
    config_error = function(e) handle_error(e, err_sink, EXIT_USAGE),
    api_error = function(e) handle_error(e, err_sink, EXIT_UNAVAILABLE)
  )
}

sink_for <- function(config, client, out_sink, err_sink) {
  if (isTRUE(config$as_new_pedigree)) {
    return(make_new_pedigree_sink(client, out_sink))
  }
  if (!is.null(config$output_path)) {
    return(make_file_sink(config$output_path, err_sink))
  }
  make_stdout_sink(out_sink)
}

handle_error <- function(condition, err_sink, code) {
  cat(sprintf("error: %s\n", conditionMessage(condition)), file = err_sink)
  code
}
