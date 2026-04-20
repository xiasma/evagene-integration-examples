test_that("produces one row per model in registry order", {
  comparison <- build_comparison(load_all_fixtures())

  expect_length(comparison$rows, 3L)
  expect_equal(
    vapply(comparison$rows, function(row) row$Model, character(1L)),
    c("BRCAPRO", "MMRpro", "PancPRO")
  )
})

test_that("columns include Model, Counselee, Any carrier and a lifetime column", {
  comparison <- build_comparison(load_all_fixtures())

  expect_equal(comparison$columns[[1L]], "Model")
  expect_equal(comparison$columns[[2L]], "Counselee")
  expect_equal(comparison$columns[[3L]], "Any carrier")
  expect_equal(tail(comparison$columns, 1L), "Lifetime risk @max-age")
})

test_that("unions gene columns across all three models in first-seen order", {
  comparison <- build_comparison(load_all_fixtures())

  gene_cols <- setdiff(
    comparison$columns,
    c("Model", "Counselee", "Any carrier", "Lifetime risk @max-age")
  )
  expect_equal(
    gene_cols,
    c("Pr(BRCA1 mutation)", "Pr(BRCA2 mutation)", "Pr(Both genes mutated)",
      "Pr(MLH1 mutation)", "Pr(MSH2 mutation)", "Pr(MSH6)")
  )
})

test_that("BRCAPRO row carries BRCA1 number and leaves MLH1 cell empty", {
  comparison <- build_comparison(load_all_fixtures())
  brcapro_row <- comparison$rows[[1L]]

  expect_equal(brcapro_row[["Pr(BRCA1 mutation)"]], 0.4239)
  expect_null(brcapro_row[["Pr(MLH1 mutation)"]])
})

test_that("lifetime summary picks the oldest age and formats percentages", {
  comparison <- build_comparison(load_all_fixtures())
  brcapro_row <- comparison$rows[[1L]]

  expect_equal(
    brcapro_row[["Lifetime risk @max-age"]],
    "Breast Ca Risk 38.48%; Ovarian Ca Risk 28.46%"
  )
})

test_that("missing carrier_probabilities raises response_schema_error", {
  expect_error(
    build_comparison(list(BRCAPRO = list(counselee_name = "X"))),
    class = "response_schema_error"
  )
})

test_that("non-numeric carrier probability raises response_schema_error", {
  bad <- list(BRCAPRO = list(
    counselee_name = "X",
    carrier_probabilities = list(`Pr(BRCA1 mutation)` = "oops"),
    future_risks = list()
  ))
  expect_error(build_comparison(bad), class = "response_schema_error")
})

test_that("empty payload list raises response_schema_error", {
  expect_error(build_comparison(list()), class = "response_schema_error")
})
