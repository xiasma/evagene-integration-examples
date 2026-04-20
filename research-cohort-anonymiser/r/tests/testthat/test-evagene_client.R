make_recording_gateway <- function(response) {
  state <- new.env(parent = emptyenv())
  state$last <- NULL
  gateway <- function(request) {
    state$last <- request
    response
  }
  attr(gateway, "state") <- state
  gateway
}

json_response <- function(status, body) {
  list(status = as.integer(status), json_body = jsonlite::toJSON(body, auto_unbox = TRUE))
}

empty_response <- function(status = 204L) {
  list(status = as.integer(status), json_body = "")
}

test_that("get_pedigree_detail issues GET and returns parsed body", {
  gateway <- make_recording_gateway(json_response(200L, list(id = "abc", individuals = list())))
  client <- make_evagene_client(gateway, "https://evagene.example", "evg_test")

  detail <- client$get_pedigree_detail("abc")
  state <- attr(gateway, "state")

  expect_equal(state$last$method, "GET")
  expect_equal(state$last$url, "https://evagene.example/api/pedigrees/abc")
  expect_equal(state$last$headers[["X-API-Key"]], "evg_test")
  expect_equal(detail$id, "abc")
})

test_that("non-2xx raises api_error", {
  gateway <- make_recording_gateway(json_response(500L, list()))
  client <- make_evagene_client(gateway, "https://evagene.example", "evg_test")

  expect_error(client$get_pedigree_detail("abc"), class = "api_error")
})

test_that("create_pedigree returns id", {
  gateway <- make_recording_gateway(json_response(201L, list(id = "new-ped-id")))
  client <- make_evagene_client(gateway, "https://evagene.example", "evg_test")

  new_id <- client$create_pedigree("Anon family")
  state <- attr(gateway, "state")

  expect_equal(new_id, "new-ped-id")
  expect_match(state$last$body_json, "\"display_name\":\"Anon family\"")
})

test_that("add_individual_to_pedigree tolerates empty response body", {
  gateway <- make_recording_gateway(empty_response())
  client <- make_evagene_client(gateway, "https://evagene.example", "evg_test")

  expect_silent(client$add_individual_to_pedigree("ped-id", "ind-id"))
  state <- attr(gateway, "state")

  expect_equal(state$last$method, "POST")
  expect_equal(state$last$url, "https://evagene.example/api/pedigrees/ped-id/individuals/ind-id")
})

test_that("designate_as_proband tolerates empty response body", {
  gateway <- make_recording_gateway(empty_response())
  client <- make_evagene_client(gateway, "https://evagene.example", "evg_test")

  expect_silent(client$designate_as_proband("ind-id"))
  state <- attr(gateway, "state")

  expect_equal(state$last$method, "PATCH")
  expect_match(state$last$body_json, "\"proband\":1")
})
