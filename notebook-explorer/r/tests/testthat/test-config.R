test_that("load_config requires EVAGENE_API_KEY", {
  expect_error(load_config(list()), class = "config_error")
})

test_that("load_config defaults base_url to the public host", {
  config <- load_config(list(EVAGENE_API_KEY = "evg_test"))
  expect_equal(config$base_url, "https://evagene.net")
  expect_equal(config$api_key, "evg_test")
})

test_that("load_config honours EVAGENE_BASE_URL and strips trailing slash", {
  config <- load_config(list(
    EVAGENE_API_KEY = "evg_test",
    EVAGENE_BASE_URL = "https://evagene.example/"
  ))
  expect_equal(config$base_url, "https://evagene.example")
})
