fixture_path <- function(name) {
  normalizePath(
    file.path("..", "..", "..", "fixtures", paste0(name, ".json")),
    mustWork = TRUE
  )
}

load_fixture <- function(name) {
  jsonlite::fromJSON(fixture_path(name), simplifyVector = FALSE)
}

test_that("near_population parses to known category with no triggers", {
  outcome <- classify_nice_response(load_fixture("near_population"))

  expect_equal(outcome$category, "near_population")
  expect_false(outcome$refer_for_genetics_assessment)
  expect_length(outcome$triggers, 0L)
})

test_that("moderate exposes a single trigger", {
  outcome <- classify_nice_response(load_fixture("moderate"))

  expect_equal(outcome$category, "moderate")
  expect_true(outcome$refer_for_genetics_assessment)
  expect_length(outcome$triggers, 1L)
})

test_that("high exposes all triggers", {
  outcome <- classify_nice_response(load_fixture("high"))

  expect_equal(outcome$category, "high")
  expect_true(outcome$refer_for_genetics_assessment)
  expect_length(outcome$triggers, 2L)
})

test_that("missing cancer_risk block raises response_schema_error", {
  expect_error(
    classify_nice_response(list(model = "NICE")),
    class = "response_schema_error"
  )
})

test_that("unknown category raises response_schema_error", {
  expect_error(
    classify_nice_response(list(
      cancer_risk = list(
        nice_category = "catastrophic",
        nice_refer_genetics = TRUE,
        nice_triggers = list(),
        notes = list()
      )
    )),
    class = "response_schema_error"
  )
})

test_that("non-string trigger raises response_schema_error", {
  expect_error(
    classify_nice_response(list(
      cancer_risk = list(
        nice_category = "moderate",
        nice_refer_genetics = TRUE,
        nice_triggers = list("ok", 42),
        notes = list()
      )
    )),
    class = "response_schema_error"
  )
})
