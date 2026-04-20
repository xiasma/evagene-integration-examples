# Write a traffic_light_report to a text sink.

#' Write a traffic_light_report to a writable connection.
#'
#' @param report A `traffic_light_report`.
#' @param sink A writable connection (e.g. `stdout()`).
present <- function(report, sink) {
  cat(sprintf("%-6s %s\n", report$colour, report$headline), file = sink)
  for (trigger in report$outcome$triggers) {
    cat(sprintf("  - %s\n", trigger), file = sink)
  }
  invisible(NULL)
}
