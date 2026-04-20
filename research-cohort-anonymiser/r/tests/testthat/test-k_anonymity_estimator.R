individual_stub <- function(sex, birth_year, disease_count) {
  diseases <- lapply(seq_len(disease_count), function(i) {
    list(disease_id = sprintf("d%d", i), affection_status = "affected")
  })
  list(
    biological_sex = sex,
    events = list(list(type = "birth", date_start = sprintf("%s-01-01", birth_year))),
    diseases = diseases
  )
}

test_that("k equals smallest bucket size", {
  pedigree <- list(individuals = list(
    individual_stub("female", "1940", 1L),
    individual_stub("female", "1940", 1L),
    individual_stub("male", "1940", 0L)
  ))

  estimate <- estimate_k_anonymity(pedigree)

  expect_equal(estimate$k, 1L)
  expect_equal(estimate$bucket_count, 2L)
  expect_equal(estimate$smallest_bucket_key, c("male", "1940", "0"))
})

test_that("homogeneous cohort reports k equal to cohort size", {
  pedigree <- list(individuals = replicate(5L,
                                           individual_stub("female", "1970", 0L),
                                           simplify = FALSE))

  estimate <- estimate_k_anonymity(pedigree)

  expect_equal(estimate$k, 5L)
  expect_equal(estimate$bucket_count, 1L)
})

test_that("empty pedigree yields zero k", {
  estimate <- estimate_k_anonymity(list(individuals = list()))

  expect_equal(estimate$k, 0L)
  expect_equal(estimate$bucket_count, 0L)
  expect_null(estimate$smallest_bucket_key)
})
