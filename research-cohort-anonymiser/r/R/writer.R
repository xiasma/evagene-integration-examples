# Write the anonymised JSON to stdout, a file, or a new Evagene pedigree.
#
# Each output mode is a small closure that emits given the rendered JSON
# and the anonymised pedigree list.  The app picks one based on config
# and never branches again.

#' Write the rendered JSON to an injected connection.
make_stdout_sink <- function(out_sink) {
  force(out_sink)
  function(rendered_json, anonymised) {
    cat(rendered_json, file = out_sink)
    invisible(NULL)
  }
}

#' Write the rendered JSON to a file, and confirm to err_sink.
make_file_sink <- function(path, err_sink) {
  force(path)
  force(err_sink)
  function(rendered_json, anonymised) {
    writeLines(rendered_json, con = path, useBytes = TRUE, sep = "")
    cat(sprintf("wrote %s\n", path), file = err_sink)
    invisible(NULL)
  }
}

#' Create a fresh pedigree on the account via the intake-form primitives.
make_new_pedigree_sink <- function(client, confirmation_sink) {
  force(client)
  force(confirmation_sink)
  function(rendered_json, anonymised) {
    new_id <- client$rebuild_pedigree(anonymised)
    cat(sprintf("%s\n", new_id), file = confirmation_sink)
    invisible(NULL)
  }
}
