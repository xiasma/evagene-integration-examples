# Map a nice_outcome to a traffic_light_report.

colour_by_category <- c(
  near_population = "GREEN",
  moderate = "AMBER",
  high = "RED"
)

headline_templates <- c(
  near_population = "Near-population risk for %s \u2014 no enhanced surveillance required.",
  moderate = "Moderate risk for %s \u2014 refer if further history emerges.",
  high = "High risk for %s \u2014 refer for genetics assessment."
)

#' Map a nice_outcome to a traffic_light_report.
#'
#' @param outcome A `nice_outcome` as returned by `classify_nice_response()`.
#' @return A `traffic_light_report` list with fields colour, headline, outcome.
to_traffic_light <- function(outcome) {
  name <- if (nzchar(outcome$counselee_name)) outcome$counselee_name else "counselee"
  report <- list(
    colour = unname(colour_by_category[[outcome$category]]),
    headline = sprintf(headline_templates[[outcome$category]], name),
    outcome = outcome
  )
  class(report) <- "traffic_light_report"
  report
}
