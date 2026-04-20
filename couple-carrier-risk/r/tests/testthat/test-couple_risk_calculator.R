ar_row <- function(name, cf, couple = NULL) {
  list(
    disease_name = name,
    inheritance_pattern = INHERITANCE_AR,
    carrier_frequency = cf,
    couple_offspring_risk = couple
  )
}

xlr_row <- function(name, cf, couple = NULL) {
  list(
    disease_name = name,
    inheritance_pattern = INHERITANCE_XLR,
    carrier_frequency = cf,
    couple_offspring_risk = couple
  )
}

risks_named_by_disease <- function(...) {
  entries <- list(...)
  stats::setNames(entries, vapply(entries, function(e) e$disease_name, character(1L)))
}

test_that("parse_population_risks indexes by disease_name", {
  indexed <- parse_population_risks(load_json_fixture("sample-population-risks"))

  expect_setequal(
    names(indexed),
    c("Sickle cell anaemia", "Cystic fibrosis", "Duchenne muscular dystrophy")
  )
  expect_equal(indexed[["Sickle cell anaemia"]]$inheritance_pattern, INHERITANCE_AR)
})

test_that("parse_population_risks raises without a 'risks' list", {
  expect_error(parse_population_risks(list()), class = "response_schema_error")
})

test_that("AR cross-partner risk is cf_a * cf_b / 4", {
  partner_a <- list(
    biological_sex = SEX_MALE,
    risks = risks_named_by_disease(ar_row("Sickle cell", 0.08, couple = 0.0016))
  )
  partner_b <- list(
    biological_sex = SEX_FEMALE,
    risks = risks_named_by_disease(ar_row("Sickle cell", 0.05, couple = 0.000625))
  )

  rows <- build_couple_rows(partner_a, partner_b)

  expect_length(rows, 1L)
  expect_equal(rows[[1L]]$carrier_frequency_a, 0.08)
  expect_equal(rows[[1L]]$carrier_frequency_b, 0.05)
  expect_equal(rows[[1L]]$cross_partner_offspring_risk, 0.08 * 0.05 / 4)
})

test_that("AR with one missing cf yields no cross-partner risk", {
  partner_a <- list(
    biological_sex = SEX_MALE,
    risks = risks_named_by_disease(ar_row("X", 0.05, couple = 0.0006))
  )
  partner_b <- list(biological_sex = SEX_FEMALE, risks = list())

  rows <- build_couple_rows(partner_a, partner_b)

  expect_null(rows[[1L]]$cross_partner_offspring_risk)
  expect_null(rows[[1L]]$carrier_frequency_b)
})

test_that("XLR uses only the female partner's carrier frequency", {
  partner_a <- list(
    biological_sex = SEX_MALE,
    risks = risks_named_by_disease(xlr_row("DMD", 0, couple = 0))
  )
  partner_b <- list(
    biological_sex = SEX_FEMALE,
    risks = risks_named_by_disease(xlr_row("DMD", 0.002, couple = 0.0005))
  )

  rows <- build_couple_rows(partner_a, partner_b)

  expect_equal(rows[[1L]]$cross_partner_offspring_risk, 0.002 / 4)
})

test_that("XLR with two male partners yields no cross-partner risk", {
  partner_a <- list(
    biological_sex = SEX_MALE,
    risks = risks_named_by_disease(xlr_row("DMD", 0.002))
  )
  partner_b <- list(
    biological_sex = SEX_MALE,
    risks = risks_named_by_disease(xlr_row("DMD", 0.002))
  )

  rows <- build_couple_rows(partner_a, partner_b)
  expect_null(rows[[1L]]$cross_partner_offspring_risk)
})

test_that("row order is partner-A then B-only entries", {
  partner_a <- list(
    biological_sex = SEX_MALE,
    risks = risks_named_by_disease(
      ar_row("A-only", 0.01),
      ar_row("Shared", 0.02)
    )
  )
  partner_b <- list(
    biological_sex = SEX_FEMALE,
    risks = risks_named_by_disease(
      ar_row("Shared", 0.03),
      ar_row("B-only", 0.04)
    )
  )

  rows <- build_couple_rows(partner_a, partner_b)

  expect_equal(
    vapply(rows, function(row) row$disease_name, character(1L)),
    c("A-only", "Shared", "B-only")
  )
})

test_that("non-numeric carrier frequency raises response_schema_error", {
  bad <- list(
    disease_name = "Bad",
    inheritance_pattern = INHERITANCE_AR,
    carrier_frequency = "oops"
  )
  partner_a <- list(
    biological_sex = SEX_MALE,
    risks = stats::setNames(list(bad), "Bad")
  )
  partner_b <- list(biological_sex = SEX_FEMALE, risks = list())

  expect_error(
    build_couple_rows(partner_a, partner_b),
    class = "response_schema_error"
  )
})
