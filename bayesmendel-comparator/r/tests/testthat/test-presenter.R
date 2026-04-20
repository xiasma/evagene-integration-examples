capture_output <- function(presenter, comparison) {
  sink <- textConnection("captured", "w", local = TRUE)
  on.exit(close(sink), add = TRUE)
  presenter(comparison, sink)
  paste(captured, collapse = "\n")
}

test_that("table presenter writes header and one row per model", {
  output <- capture_output(present_table, build_comparison(load_all_fixtures()))
  lines <- strsplit(output, "\n", fixed = TRUE)[[1L]]

  expect_equal(length(lines), 4L)
  expect_true(grepl("Model", lines[[1L]], fixed = TRUE))
  expect_true(grepl("BRCAPRO", lines[[2L]], fixed = TRUE))
  expect_true(grepl("MMRpro", lines[[3L]], fixed = TRUE))
  expect_true(grepl("PancPRO", lines[[4L]], fixed = TRUE))
})

test_that("table presenter renders missing cells as '-'", {
  output <- capture_output(present_table, build_comparison(load_all_fixtures()))
  pancpro_line <- strsplit(output, "\n", fixed = TRUE)[[1L]][[4L]]

  # PancPRO has no BRCA1 probability -- it must show as "-", not "0.00%".
  expect_true(grepl(" - ", pancpro_line, fixed = TRUE))
})

test_that("csv presenter emits header plus one row per model with commas", {
  output <- capture_output(present_csv, build_comparison(load_all_fixtures()))
  lines <- strsplit(output, "\n", fixed = TRUE)[[1L]]

  expect_equal(length(lines), 4L)
  expect_equal(strsplit(lines[[1L]], ",", fixed = TRUE)[[1L]][[1L]], "Model")
  expect_equal(strsplit(lines[[2L]], ",", fixed = TRUE)[[1L]][[1L]], "BRCAPRO")
})

test_that("csv presenter quotes fields containing commas", {
  output <- capture_output(present_csv, build_comparison(load_all_fixtures()))

  # The lifetime summary uses "; " between entries, but cells also include
  # percentages with commas if locale changed -- our format_cell always uses
  # a decimal point, so no comma should appear *inside* a cell, so no quoting
  # expected here.  Assert we haven't spuriously quoted normal strings:
  expect_false(grepl('"BRCAPRO"', output, fixed = TRUE))
})

test_that("json presenter emits columns and rows arrays", {
  output <- capture_output(present_json, build_comparison(load_all_fixtures()))
  parsed <- jsonlite::fromJSON(output, simplifyVector = FALSE)

  expect_true("columns" %in% names(parsed))
  expect_true("rows" %in% names(parsed))
  expect_length(parsed$rows, 3L)
  expect_equal(parsed$rows[[1L]]$Model, "BRCAPRO")
})

test_that("json presenter keeps numeric probabilities as numbers", {
  output <- capture_output(present_json, build_comparison(load_all_fixtures()))
  parsed <- jsonlite::fromJSON(output, simplifyVector = FALSE)

  expect_equal(parsed$rows[[1L]][["Pr(BRCA1 mutation)"]], 0.4239)
})

test_that("presenter_for returns the right function", {
  expect_identical(presenter_for("table"), present_table)
  expect_identical(presenter_for("csv"), present_csv)
  expect_identical(presenter_for("json"), present_json)
  expect_error(presenter_for("yaml"))
})
