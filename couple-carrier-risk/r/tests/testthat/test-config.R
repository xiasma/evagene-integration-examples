minimal_argv <- function(...) {
  c("--partner-a", "a.txt", "--partner-b", "b.txt", ...)
}

env_with_key <- function(extra = list()) {
  c(list(EVAGENE_API_KEY = "evg_test"), extra)
}

test_that("defaults base URL, output table, auto ancestry, and cleanup on", {
  config <- load_config(minimal_argv(), env_with_key())

  expect_equal(config$base_url, "https://evagene.net")
  expect_equal(config$api_key, "evg_test")
  expect_equal(config$partner_a_file, "a.txt")
  expect_equal(config$partner_b_file, "b.txt")
  expect_equal(config$ancestry_a, "auto")
  expect_equal(config$ancestry_b, "auto")
  expect_equal(config$output, "table")
  expect_true(config$cleanup)
})

test_that("honours a custom base URL", {
  config <- load_config(
    minimal_argv(),
    env_with_key(list(EVAGENE_BASE_URL = "https://evagene.example"))
  )
  expect_equal(config$base_url, "https://evagene.example")
})

test_that("accepts --output csv and --output json", {
  for (fmt in c("csv", "json")) {
    config <- load_config(minimal_argv("--output", fmt), env_with_key())
    expect_equal(config$output, fmt)
  }
})

test_that("rejects unknown --output", {
  expect_error(
    load_config(minimal_argv("--output", "yaml"), env_with_key()),
    class = "config_error"
  )
})

test_that("--no-cleanup overrides the default", {
  config <- load_config(minimal_argv("--no-cleanup"), env_with_key())
  expect_false(config$cleanup)
})

test_that("carries --ancestry-a and --ancestry-b flags", {
  config <- load_config(
    minimal_argv("--ancestry-a", "ashkenazi_jewish", "--ancestry-b", "mediterranean"),
    env_with_key()
  )
  expect_equal(config$ancestry_a, "ashkenazi_jewish")
  expect_equal(config$ancestry_b, "mediterranean")
})

test_that("missing API key raises config_error", {
  expect_error(
    load_config(minimal_argv(), list()),
    class = "config_error"
  )
})

test_that("partner files are required", {
  expect_error(
    load_config(c("--partner-a", "a.txt"), env_with_key()),
    class = "config_error"
  )
})
