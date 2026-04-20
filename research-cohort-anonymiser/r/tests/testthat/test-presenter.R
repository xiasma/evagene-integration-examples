sample_anonymised <- function() {
  list(
    display_name = "Anonymised pedigree",
    date_represented = "1980-01-01",
    properties = list(clinic_reference = "X"),
    individuals = list(list(
      id = "a",
      display_name = "I-1",
      generation_label = "I",
      biological_sex = "female",
      proband = 0L,
      proband_text = "",
      events = list(list(type = "birth", date_start = "1950-01-01",
                         date_end = "1950-01-01", properties = list())),
      diseases = list(list(disease_id = "BC", affection_status = "affected",
                           manifestations = list())),
      properties = list()
    )),
    relationships = list(),
    eggs = list()
  )
}

sample_estimate <- function() {
  list(k = 1L, bucket_count = 1L,
       smallest_bucket_key = c("female", "1950", "1"),
       total_individuals = 1L)
}

test_that("top-level keys are emitted in declared order", {
  rendered <- render_json(sample_anonymised(), sample_estimate())
  document <- jsonlite::fromJSON(rendered, simplifyVector = FALSE)
  expect_equal(names(document), c(
    "display_name", "date_represented", "properties",
    "individuals", "relationships", "eggs", "k_anonymity"
  ))
})

test_that("individual fields are emitted in declared order", {
  rendered <- render_json(sample_anonymised(), sample_estimate())
  document <- jsonlite::fromJSON(rendered, simplifyVector = FALSE)
  expect_equal(names(document$individuals[[1L]]), c(
    "id", "display_name", "generation_label", "biological_sex",
    "proband", "proband_text", "events", "diseases", "properties"
  ))
})

test_that("two renders of same input are byte-identical", {
  first <- render_json(sample_anonymised(), sample_estimate())
  second <- render_json(sample_anonymised(), sample_estimate())
  expect_identical(first, second)
})

test_that("render ends with a trailing newline", {
  rendered <- render_json(sample_anonymised(), sample_estimate())
  expect_true(endsWith(rendered, "\n"))
})
