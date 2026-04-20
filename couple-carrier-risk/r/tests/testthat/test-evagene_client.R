recording_gateway <- function(queue) {
  state <- new.env(parent = emptyenv())
  state$calls <- list()
  state$queue <- queue

  gateway <- function(request) {
    state$calls[[length(state$calls) + 1L]] <- request
    response <- state$queue[[1L]]
    state$queue <- state$queue[-1L]
    response
  }
  list(gateway = gateway, state = state)
}

ok_response <- function(status, body) {
  list(status = status, json_body = body)
}

test_that("create_pedigree posts display_name and returns id", {
  recorder <- recording_gateway(list(
    ok_response(201L, '{"id": "ped-uuid", "display_name": "scratch"}')
  ))

  pedigree_id <- create_pedigree(
    recorder$gateway, "https://evagene.example", "evg_test", "scratch"
  )

  expect_equal(pedigree_id, "ped-uuid")
  call <- recorder$state$calls[[1L]]
  expect_equal(call$method, "POST")
  expect_equal(call$url, "https://evagene.example/api/pedigrees")
  expect_equal(unname(call$headers[["X-API-Key"]]), "evg_test")
  body <- jsonlite::fromJSON(call$body_json, simplifyVector = FALSE)
  expect_equal(body$display_name, "scratch")
})

test_that("create_individual sends biological_sex when known", {
  recorder <- recording_gateway(list(ok_response(201L, '{"id": "ind-uuid"}')))

  identifier <- create_individual(
    recorder$gateway, "https://evagene.example", "evg_test",
    "Partner A", SEX_MALE
  )

  expect_equal(identifier, "ind-uuid")
  body <- jsonlite::fromJSON(recorder$state$calls[[1L]]$body_json, simplifyVector = FALSE)
  expect_equal(body$biological_sex, "male")
})

test_that("create_individual omits biological_sex when unknown", {
  recorder <- recording_gateway(list(ok_response(201L, '{"id": "ind-uuid"}')))

  create_individual(
    recorder$gateway, "https://evagene.example", "evg_test",
    "Partner A", SEX_UNKNOWN
  )

  body <- jsonlite::fromJSON(recorder$state$calls[[1L]]$body_json, simplifyVector = FALSE)
  expect_null(body$biological_sex)
})

test_that("add_individual_to_pedigree posts empty body at the correct URL", {
  recorder <- recording_gateway(list(ok_response(204L, "")))

  add_individual_to_pedigree(
    recorder$gateway, "https://evagene.example", "evg_test", "ped-id", "ind-id"
  )

  call <- recorder$state$calls[[1L]]
  expect_equal(call$method, "POST")
  expect_equal(call$url, "https://evagene.example/api/pedigrees/ped-id/individuals/ind-id")
  expect_null(call$body_json)
})

test_that("import_23andme_raw puts individual_id in query and tsv in body", {
  recorder <- recording_gateway(list(ok_response(200L, '{"tests_added": 1}')))

  import_23andme_raw(
    recorder$gateway, "https://evagene.example", "evg_test",
    "ped-id", "ind-id", "# synthetic\nrs334\t11\t5248232\tAT\n"
  )

  call <- recorder$state$calls[[1L]]
  expect_equal(call$url, "https://evagene.example/api/pedigrees/ped-id/import/23andme-raw")
  expect_equal(unname(call$params[["individual_id"]]), "ind-id")
  body <- jsonlite::fromJSON(call$body_json, simplifyVector = FALSE)
  expect_true(grepl("rs334", body$content, fixed = TRUE))
})

test_that("get_population_risks returns parsed payload", {
  recorder <- recording_gateway(list(
    ok_response(200L, '{"individual_id": "ind-id", "risks": []}')
  ))

  payload <- get_population_risks(
    recorder$gateway, "https://evagene.example", "evg_test", "ind-id"
  )

  expect_equal(payload$individual_id, "ind-id")
  expect_equal(recorder$state$calls[[1L]]$method, "GET")
})

test_that("find_ancestry_id_by_population_key finds matching entry", {
  recorder <- recording_gateway(list(
    ok_response(200L, '[
      {"id": "anc-1", "population_key": "general"},
      {"id": "anc-2", "population_key": "mediterranean"}
    ]')
  ))

  result <- find_ancestry_id_by_population_key(
    recorder$gateway, "https://evagene.example", "evg_test", "mediterranean"
  )

  expect_equal(result, "anc-2")
})

test_that("find_ancestry_id_by_population_key returns NULL when absent", {
  recorder <- recording_gateway(list(
    ok_response(200L, '[{"id": "anc-1", "population_key": "x"}]')
  ))

  expect_null(find_ancestry_id_by_population_key(
    recorder$gateway, "https://evagene.example", "evg_test", "missing"
  ))
})

test_that("delete_pedigree and delete_individual hit the right URLs", {
  recorder <- recording_gateway(list(
    ok_response(204L, ""),
    ok_response(204L, "")
  ))

  delete_individual(
    recorder$gateway, "https://evagene.example", "evg_test", "ind-id"
  )
  delete_pedigree(
    recorder$gateway, "https://evagene.example", "evg_test", "ped-id"
  )

  expect_equal(recorder$state$calls[[1L]]$method, "DELETE")
  expect_equal(recorder$state$calls[[1L]]$url, "https://evagene.example/api/individuals/ind-id")
  expect_equal(recorder$state$calls[[2L]]$url, "https://evagene.example/api/pedigrees/ped-id")
})

test_that("non-2xx status raises api_error with URL in message", {
  recorder <- recording_gateway(list(ok_response(500L, "boom")))

  expect_error(
    get_population_risks(recorder$gateway, "https://evagene.example", "evg_test", "ind-id"),
    class = "api_error"
  )
})

test_that("non-object JSON raises api_error", {
  recorder <- recording_gateway(list(ok_response(200L, '["not", "an", "object"]')))

  expect_error(
    get_population_risks(recorder$gateway, "https://evagene.example", "evg_test", "ind-id"),
    class = "api_error"
  )
})
