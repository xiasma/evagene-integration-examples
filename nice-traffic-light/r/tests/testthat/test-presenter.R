build_report <- function(triggers) {
  outcome <- list(
    counselee_name = "Jane Doe",
    category = "high",
    refer_for_genetics_assessment = TRUE,
    triggers = triggers,
    notes = character(0)
  )
  class(outcome) <- "nice_outcome"

  report <- list(
    colour = "RED",
    headline = "High risk for Jane Doe \u2014 refer for genetics assessment.",
    outcome = outcome
  )
  class(report) <- "traffic_light_report"
  report
}

capture_present <- function(report) {
  sink <- textConnection("captured", "w", local = TRUE)
  on.exit(close(sink), add = TRUE)
  present(report, sink)
  paste(captured, collapse = "\n")
}

test_that("writes the colour label and headline on the first line", {
  output <- capture_present(build_report(character(0)))
  first_line <- strsplit(output, "\n", fixed = TRUE)[[1L]][[1L]]

  expect_true(startsWith(first_line, "RED"))
  expect_true(grepl("Jane Doe", first_line, fixed = TRUE))
})

test_that("writes each trigger on its own indented line", {
  output <- capture_present(build_report(c("Trigger A", "Trigger B")))
  lines <- strsplit(output, "\n", fixed = TRUE)[[1L]]

  expect_equal(lines[[2L]], "  - Trigger A")
  expect_equal(lines[[3L]], "  - Trigger B")
})

test_that("writes only the headline when there are no triggers", {
  output <- capture_present(build_report(character(0)))

  expect_false(grepl("  - ", output, fixed = TRUE))
})
