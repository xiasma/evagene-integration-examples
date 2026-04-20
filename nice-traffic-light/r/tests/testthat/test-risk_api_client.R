PEDIGREE_ID <- "11111111-1111-1111-1111-111111111111"
COUNSELEE_ID <- "22222222-2222-2222-2222-222222222222"

recording_gateway <- function(status, json_body) {
  last <- new.env(parent = emptyenv())
  last$url <- NULL
  last$headers <- NULL
  last$body_json <- NULL

  gateway <- function(request) {
    last$url <- request$url
    last$headers <- request$headers
    last$body_json <- request$body_json
    list(status = status, json_body = json_body)
  }
  list(gateway = gateway, last = last)
}

test_that("posts NICE model to risk/calculate", {
  recorder <- recording_gateway(
    status = 200L,
    json_body = '{"cancer_risk": {"nice_category": "near_population"}}'
  )

  calculate_nice(
    recorder$gateway,
    base_url = "https://evagene.example",
    api_key = "evg_test",
    pedigree_id = PEDIGREE_ID
  )

  expect_equal(
    recorder$last$url,
    sprintf("https://evagene.example/api/pedigrees/%s/risk/calculate", PEDIGREE_ID)
  )
  expect_equal(unname(recorder$last$headers[["X-API-Key"]]), "evg_test")

  body <- jsonlite::fromJSON(recorder$last$body_json, simplifyVector = FALSE)
  expect_equal(body$model, "NICE")
  expect_null(body$counselee_id)
})

test_that("includes counselee_id when provided", {
  recorder <- recording_gateway(status = 200L, json_body = '{}')

  calculate_nice(
    recorder$gateway,
    base_url = "https://evagene.example",
    api_key = "evg_test",
    pedigree_id = PEDIGREE_ID,
    counselee_id = COUNSELEE_ID
  )

  body <- jsonlite::fromJSON(recorder$last$body_json, simplifyVector = FALSE)
  expect_equal(body$counselee_id, COUNSELEE_ID)
})

test_that("raises api_error on non-2xx status", {
  recorder <- recording_gateway(status = 500L, json_body = '{}')

  expect_error(
    calculate_nice(recorder$gateway, "https://evagene.example", "evg_test", PEDIGREE_ID),
    class = "api_error"
  )
})

test_that("raises api_error on non-object JSON", {
  recorder <- recording_gateway(status = 200L, json_body = '["not","an","object"]')

  expect_error(
    calculate_nice(recorder$gateway, "https://evagene.example", "evg_test", PEDIGREE_ID),
    class = "api_error"
  )
})
