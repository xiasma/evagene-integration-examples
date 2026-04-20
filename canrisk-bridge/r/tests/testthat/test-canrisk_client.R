PEDIGREE_ID <- "11111111-1111-1111-1111-111111111111"

sample_canrisk <- function() {
  path <- normalizePath(
    file.path("..", "..", "..", "fixtures", "sample-canrisk.txt"),
    mustWork = TRUE
  )
  paste(readLines(path, warn = FALSE), collapse = "\n")
}

recording_gateway <- function(status, body) {
  last <- new.env(parent = emptyenv())
  last$url <- NULL
  last$headers <- NULL

  gateway <- function(request) {
    last$url <- request$url
    last$headers <- request$headers
    list(status = status, body = body)
  }
  list(gateway = gateway, last = last)
}

test_that("GETs the canrisk endpoint with the documented headers", {
  recorder <- recording_gateway(status = 200L, body = sample_canrisk())

  body <- fetch_canrisk(
    recorder$gateway,
    base_url = "https://evagene.example",
    api_key = "evg_test",
    pedigree_id = PEDIGREE_ID
  )

  expect_equal(
    recorder$last$url,
    sprintf("https://evagene.example/api/pedigrees/%s/risk/canrisk", PEDIGREE_ID)
  )
  expect_equal(unname(recorder$last$headers[["X-API-Key"]]), "evg_test")
  expect_equal(unname(recorder$last$headers[["Accept"]]), "text/tab-separated-values")
  expect_true(startsWith(body, CANRISK_HEADER))
})

test_that("raises api_error on non-2xx status", {
  recorder <- recording_gateway(status = 500L, body = "")

  expect_error(
    fetch_canrisk(recorder$gateway, "https://evagene.example", "evg_test", PEDIGREE_ID),
    class = "api_error"
  )
})

test_that("raises canrisk_format_error when header is missing", {
  recorder <- recording_gateway(status = 200L, body = "not a canrisk file")

  expect_error(
    fetch_canrisk(recorder$gateway, "https://evagene.example", "evg_test", PEDIGREE_ID),
    class = "canrisk_format_error"
  )
})
