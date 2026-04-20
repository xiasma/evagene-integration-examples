PEDIGREE_ID <- "11111111-1111-1111-1111-111111111111"

recording_gateway <- function(status, body_text) {
  last <- new.env(parent = emptyenv())
  last$method <- NULL
  last$url <- NULL
  last$headers <- NULL

  gateway <- function(request) {
    last$method <- request$method
    last$url <- request$url
    last$headers <- request$headers
    list(status = status, body_text = body_text)
  }
  list(gateway = gateway, last = last)
}

test_that("fetch_pedigree_svg issues a GET to /export.svg and returns the raw SVG text", {
  recorder <- recording_gateway(
    status = 200L,
    body_text = "<svg xmlns=\"http://www.w3.org/2000/svg\"/>"
  )

  svg_text <- fetch_pedigree_svg(
    recorder$gateway, "https://evagene.example", "evg_test", PEDIGREE_ID
  )

  expect_equal(recorder$last$method, "GET")
  expect_equal(
    recorder$last$url,
    sprintf("https://evagene.example/api/pedigrees/%s/export.svg", PEDIGREE_ID)
  )
  expect_equal(unname(recorder$last$headers[["X-API-Key"]]), "evg_test")
  expect_equal(unname(recorder$last$headers[["Accept"]]), "image/svg+xml")
  expect_equal(svg_text, "<svg xmlns=\"http://www.w3.org/2000/svg\"/>")
})

test_that("fetch_pedigree_svg trims a trailing slash on the base URL", {
  recorder <- recording_gateway(status = 200L, body_text = "<svg/>")

  fetch_pedigree_svg(
    recorder$gateway, "https://evagene.example/", "evg_test", PEDIGREE_ID
  )

  expect_equal(
    recorder$last$url,
    sprintf("https://evagene.example/api/pedigrees/%s/export.svg", PEDIGREE_ID)
  )
})

test_that("fetch_pedigree_svg raises api_error on a non-2xx response", {
  recorder <- recording_gateway(status = 500L, body_text = "boom")

  expect_error(
    fetch_pedigree_svg(
      recorder$gateway, "https://evagene.example", "evg_test", PEDIGREE_ID
    ),
    class = "api_error"
  )
})

test_that("fetch_pedigree_detail parses JSON into a named list", {
  body <- '{"id":"abc","individuals":[{"id":"x","display_name":"Alice"}]}'
  recorder <- recording_gateway(status = 200L, body_text = body)

  detail <- fetch_pedigree_detail(
    recorder$gateway, "https://evagene.example", "evg_test", PEDIGREE_ID
  )

  expect_equal(
    recorder$last$url,
    sprintf("https://evagene.example/api/pedigrees/%s", PEDIGREE_ID)
  )
  expect_equal(detail$id, "abc")
  expect_equal(detail$individuals[[1L]]$display_name, "Alice")
})

test_that("fetch_pedigree_detail raises api_error on invalid JSON", {
  recorder <- recording_gateway(status = 200L, body_text = "{ not json")

  expect_error(
    fetch_pedigree_detail(
      recorder$gateway, "https://evagene.example", "evg_test", PEDIGREE_ID
    ),
    class = "api_error"
  )
})
