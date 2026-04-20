VALID_UUID <- "11111111-1111-1111-1111-111111111111"

test_that("defaults base URL, format table, and no counselee when unset", {
  config <- load_config(c(VALID_UUID), list(EVAGENE_API_KEY = "evg_test"))

  expect_equal(config$base_url, "https://evagene.net")
  expect_equal(config$api_key, "evg_test")
  expect_equal(config$pedigree_id, VALID_UUID)
  expect_null(config$counselee_id)
  expect_equal(config$format, "table")
})

test_that("honours a custom base URL", {
  config <- load_config(
    c(VALID_UUID),
    list(EVAGENE_API_KEY = "evg_test", EVAGENE_BASE_URL = "https://evagene.example")
  )
  expect_equal(config$base_url, "https://evagene.example")
})

test_that("accepts --format csv and --format json", {
  for (fmt in c("csv", "json")) {
    config <- load_config(
      c(VALID_UUID, "--format", fmt),
      list(EVAGENE_API_KEY = "evg_test")
    )
    expect_equal(config$format, fmt)
  }
})

test_that("rejects unknown --format", {
  expect_error(
    load_config(
      c(VALID_UUID, "--format", "yaml"),
      list(EVAGENE_API_KEY = "evg_test")
    ),
    class = "config_error"
  )
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

test_that("counselee must be a UUID when provided", {
  expect_error(
    load_config(
      c(VALID_UUID, "--counselee", "oops"),
      list(EVAGENE_API_KEY = "evg_test")
    ),
    class = "config_error"
  )
})
