# Composition root -- wires config, api client, label mapper, svg
# deidentifier, and output writer.

EXIT_OK <- 0L
EXIT_USAGE <- 64L
EXIT_UNAVAILABLE <- 69L
EXIT_INVALID_SVG <- 70L

#' Run the publication-figure renderer pipeline end-to-end.
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
    svg_text <- fetch_pedigree_svg(
      gateway, config$base_url, config$api_key, config$pedigree_id
    )
    name_to_label <- if (config$deidentify) {
      build_name_to_label(gateway, config)
    } else {
      character(0)
    }
    rendered <- deidentify_svg(svg_text, name_to_label, config$width, config$height)
    write_svg(rendered, config$output_path)
    announce_written(config$output_path, out_sink)
    EXIT_OK
  },
    config_error = function(e) handle_error(e, err_sink, EXIT_USAGE),
    api_error = function(e) handle_error(e, err_sink, EXIT_UNAVAILABLE),
    invalid_svg_error = function(e) handle_error(e, err_sink, EXIT_INVALID_SVG)
  )
}

build_name_to_label <- function(gateway, config) {
  detail <- fetch_pedigree_detail(
    gateway, config$base_url, config$api_key, config$pedigree_id
  )
  id_to_label <- build_label_mapping(detail, config$label_style)
  name_to_label_mapping(detail$individuals, id_to_label)
}

# The SVG replaces <text> nodes by their current content, so the mapping
# we hand the deidentifier must be keyed by the original display name,
# not by the individual id.  Individuals with no display name contribute
# nothing to swap against.
name_to_label_mapping <- function(individuals, id_to_label) {
  if (is.null(individuals) || length(individuals) == 0L) {
    return(character(0))
  }
  out <- character(0)
  for (ind in individuals) {
    display_name <- ind$display_name
    if (!is.character(display_name) || length(display_name) != 1L ||
        is.na(display_name) || !nzchar(display_name)) {
      next
    }
    label <- id_to_label[[as.character(ind$id)]]
    out[[display_name]] <- label
  }
  out
}

announce_written <- function(path, sink) {
  cat(sprintf("Wrote %s\n", path), file = sink)
}

handle_error <- function(condition, err_sink, code) {
  cat(sprintf("error: %s\n", conditionMessage(condition)), file = err_sink)
  code
}
