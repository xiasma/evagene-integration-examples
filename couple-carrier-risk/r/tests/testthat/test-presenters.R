sample_rows <- function() {
  list(
    structure(
      list(
        disease_name = "Sickle cell anaemia",
        inheritance_pattern = INHERITANCE_AR,
        carrier_frequency_a = 0.07,
        carrier_frequency_b = 0.05,
        api_couple_offspring_risk_a = 0.001225,
        api_couple_offspring_risk_b = 0.000625,
        cross_partner_offspring_risk = 0.000875
      ),
      class = "couple_row"
    ),
    structure(
      list(
        disease_name = "Duchenne muscular dystrophy",
        inheritance_pattern = INHERITANCE_XLR,
        carrier_frequency_a = NULL,
        carrier_frequency_b = 0.0001,
        api_couple_offspring_risk_a = NULL,
        api_couple_offspring_risk_b = 0.000025,
        cross_partner_offspring_risk = 0.000025
      ),
      class = "couple_row"
    )
  )
}

capture_output <- function(presenter) {
  output_chunks <- character(0)
  sink <- textConnection("output_chunks", "w", local = TRUE)
  on.exit(close(sink), add = TRUE)
  presenter(sample_rows(), sink)
  paste(output_chunks, collapse = "\n")
}

test_that("table renders header plus one row per disease", {
  lines <- strsplit(capture_output(present_table), "\n", fixed = TRUE)[[1L]]

  expect_equal(length(lines), 3L)
  expect_true(grepl("Disease", lines[[1L]], fixed = TRUE))
  expect_true(grepl("Sickle cell anaemia", lines[[2L]], fixed = TRUE))
  expect_true(grepl("Duchenne muscular dystrophy", lines[[3L]], fixed = TRUE))
})

test_that("table renders missing cells as '-'", {
  lines <- strsplit(capture_output(present_table), "\n", fixed = TRUE)[[1L]]
  expect_true(grepl(" - ", lines[[3L]], fixed = TRUE))
})

test_that("csv emits header plus one row per disease", {
  lines <- strsplit(capture_output(present_csv), "\n", fixed = TRUE)[[1L]]

  expect_equal(length(lines), 3L)
  expect_equal(strsplit(lines[[1L]], ",", fixed = TRUE)[[1L]][[1L]], "Disease")
  expect_equal(strsplit(lines[[2L]], ",", fixed = TRUE)[[1L]][[1L]], "Sickle cell anaemia")
})

test_that("json emits columns and rows", {
  parsed <- jsonlite::fromJSON(capture_output(present_json), simplifyVector = FALSE)

  expect_true("columns" %in% names(parsed))
  expect_true("rows" %in% names(parsed))
  expect_length(parsed$rows, 2L)
  expect_equal(parsed$rows[[1L]]$Disease, "Sickle cell anaemia")
})

test_that("json keeps numbers as numbers and missing as null", {
  parsed <- jsonlite::fromJSON(capture_output(present_json), simplifyVector = FALSE)

  expect_equal(parsed$rows[[1L]][["CF(A)"]], 0.07)
  expect_null(parsed$rows[[2L]][["CF(A)"]])
})

test_that("presenter_for dispatches by name", {
  expect_identical(presenter_for("table"), present_table)
  expect_identical(presenter_for("csv"), present_csv)
  expect_identical(presenter_for("json"), present_json)
  expect_error(presenter_for("yaml"))
})
