test_that("year precision rounds to first of year", {
  expect_equal(truncate_date("1968-09-22", "year"), "1968-01-01")
})

test_that("five-year precision rounds down to nearest five", {
  expect_equal(truncate_date("1968-09-22", "five-year"), "1965-01-01")
})

test_that("decade precision rounds down to nearest ten", {
  expect_equal(truncate_date("1968-09-22", "decade"), "1960-01-01")
})

test_that("NULL date passes through as NULL", {
  expect_null(truncate_date(NULL, "year"))
})

test_that("malformed date becomes NA", {
  expect_true(is.na(truncate_date("not-a-date", "year")))
})

test_that("round_age buckets by precision", {
  expect_equal(round_age(43L, "year"), 43L)
  expect_equal(round_age(43L, "five-year"), 40L)
  expect_equal(round_age(58L, "decade"), 50L)
  expect_equal(round_age(9L, "decade"), 0L)
})

test_that("strip_free_text_properties drops note/comment/description keys", {
  cleaned <- strip_free_text_properties(list(
    death_status = "dead",
    clinical_note = "PII",
    counsellor_comment = "PII",
    long_description = "PII",
    age_at_event = 52L
  ))
  expect_equal(sort(names(cleaned)), c("age_at_event", "death_status"))
})

test_that("strip is case insensitive", {
  cleaned <- strip_free_text_properties(list(Clinical_NOTE = "redact"))
  expect_equal(length(cleaned), 0L)
})

test_that("build_stable_identifiers assigns roman-label-dash-index", {
  labels <- c(a = "I", b = "I", c = "II")
  identifiers <- build_stable_identifiers(
    labels,
    list(list(id = "a"), list(id = "b"), list(id = "c"))
  )
  expect_equal(identifiers[["a"]], "I-1")
  expect_equal(identifiers[["b"]], "I-2")
  expect_equal(identifiers[["c"]], "II-1")
})

test_that("anonymise_pedigree replaces all display names and strips source names", {
  source <- load_fixture("source-pedigree")
  labels <- assign_generation_labels(source)
  rules <- list(age_precision = "year", keep_sex = TRUE)

  result <- anonymise_pedigree(source, labels, rules)
  serialised <- jsonlite::toJSON(result, auto_unbox = TRUE)

  for (individual in source$individuals) {
    if (!is.null(individual$display_name) && nzchar(individual$display_name)) {
      expect_false(grepl(individual$display_name, serialised, fixed = TRUE))
    }
    if (!is.null(individual$name$family) && nzchar(individual$name$family)) {
      expect_false(grepl(individual$name$family, serialised, fixed = TRUE))
    }
  }
})

test_that("anonymise_pedigree preserves consanguinity coefficient", {
  source <- load_fixture("source-pedigree")
  labels <- assign_generation_labels(source)
  rules <- list(age_precision = "year", keep_sex = TRUE)

  result <- anonymise_pedigree(source, labels, rules)
  parent_relationship <- Filter(function(r) r$id == "r-parents", result$relationships)[[1L]]
  expect_equal(parent_relationship$consanguinity, 0.0625)
})

test_that("--no-keep-sex redacts biological_sex to unknown", {
  source <- load_fixture("source-pedigree")
  labels <- assign_generation_labels(source)
  rules <- list(age_precision = "year", keep_sex = FALSE)

  result <- anonymise_pedigree(source, labels, rules)
  sexes <- vapply(result$individuals, function(i) i$biological_sex, character(1L))
  expect_true(all(sexes == "unknown"))
})

test_that("notes on individuals are not present after anonymisation", {
  source <- load_fixture("source-pedigree")
  labels <- assign_generation_labels(source)
  rules <- list(age_precision = "year", keep_sex = TRUE)

  result <- anonymise_pedigree(source, labels, rules)
  for (individual in result$individuals) {
    expect_false("notes" %in% names(individual))
  }
})
