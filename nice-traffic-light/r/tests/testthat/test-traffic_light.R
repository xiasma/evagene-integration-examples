build_outcome <- function(category) {
  outcome <- list(
    counselee_name = "Jane Doe",
    category = category,
    refer_for_genetics_assessment = category != "near_population",
    triggers = character(0),
    notes = character(0)
  )
  class(outcome) <- "nice_outcome"
  outcome
}

test_that("near_population maps to GREEN", {
  expect_equal(to_traffic_light(build_outcome("near_population"))$colour, "GREEN")
})

test_that("moderate maps to AMBER", {
  expect_equal(to_traffic_light(build_outcome("moderate"))$colour, "AMBER")
})

test_that("high maps to RED", {
  expect_equal(to_traffic_light(build_outcome("high"))$colour, "RED")
})

test_that("headline contains the counselee name", {
  report <- to_traffic_light(build_outcome("moderate"))
  expect_true(grepl("Jane Doe", report$headline, fixed = TRUE))
})

test_that("headline falls back when counselee name is empty", {
  outcome <- build_outcome("high")
  outcome$counselee_name <- ""
  report <- to_traffic_light(outcome)
  expect_true(grepl("counselee", report$headline, fixed = TRUE))
})
