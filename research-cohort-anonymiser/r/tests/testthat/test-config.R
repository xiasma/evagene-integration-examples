VALID_UUID <- "11111111-1111-1111-1111-111111111111"

test_that("defaults are year precision, keep sex, stdout", {
  config <- load_config(c(VALID_UUID), list(EVAGENE_API_KEY = "evg_test"))

  expect_equal(config$base_url, "https://evagene.net")
  expect_equal(config$api_key, "evg_test")
  expect_equal(config$pedigree_id, VALID_UUID)
  expect_null(config$output_path)
  expect_false(config$as_new_pedigree)
  expect_equal(config$age_precision, "year")
  expect_true(config$keep_sex)
})

test_that("missing API key raises config_error", {
  expect_error(
    load_config(c(VALID_UUID), list()),
    class = "config_error"
  )
})

test_that("pedigree id must be a UUID", {
  expect_error(
    load_config(c("not-a-uuid"), list(EVAGENE_API_KEY = "evg_test")),
    class = "config_error"
  )
})

test_that("--output and --as-new-pedigree are mutually exclusive", {
  expect_error(
    load_config(
      c(VALID_UUID, "--output", "out.json", "--as-new-pedigree"),
      list(EVAGENE_API_KEY = "evg_test")
    ),
    class = "config_error"
  )
})

test_that("--age-precision decade is accepted", {
  config <- load_config(
    c(VALID_UUID, "--age-precision", "decade"),
    list(EVAGENE_API_KEY = "evg_test")
  )
  expect_equal(config$age_precision, "decade")
})

test_that("--no-keep-sex flips keep_sex", {
  config <- load_config(
    c(VALID_UUID, "--no-keep-sex"),
    list(EVAGENE_API_KEY = "evg_test")
  )
  expect_false(config$keep_sex)
})
