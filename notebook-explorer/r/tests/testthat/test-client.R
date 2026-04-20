BASE_URL <- "https://evagene.example"
PEDIGREE_ID <- "11111111-1111-1111-1111-111111111111"
SCRATCH_ID <- "99999999-9999-9999-9999-999999999999"
INDIVIDUAL_ID <- "22222222-2222-2222-2222-222222222222"
RELATIVE_ID <- "33333333-3333-3333-3333-333333333333"
DISEASE_ID <- "44444444-4444-4444-4444-444444444444"

scripted_gateway <- function(responses) {
  state <- new.env(parent = emptyenv())
  state$responses <- responses
  state$calls <- list()
  gateway <- function(request) {
    state$calls[[length(state$calls) + 1L]] <- request
    if (length(state$responses) == 0L) {
      stop(sprintf("Unexpected extra call: %s %s", request$method, request$url))
    }
    head <- state$responses[[1L]]
    state$responses <- state$responses[-1L]
    head
  }
  list(gateway = gateway, state = state)
}

response <- function(status, body = NULL, text = NULL) {
  if (!is.null(body)) {
    text <- jsonlite::toJSON(body, auto_unbox = TRUE, null = "null")
  }
  if (is.null(text)) text <- ""
  list(status = as.integer(status), body_string = text)
}

build_client <- function(gateway) {
  evagene_client(gateway, BASE_URL, "evg_test")
}

# ----------------------------------------------------------- get_pedigrees

test_that("get_pedigrees returns the list from the API", {
  rec <- scripted_gateway(list(response(200, list(list(id = PEDIGREE_ID)))))
  client <- build_client(rec$gateway)

  result <- client$get_pedigrees()

  expect_equal(length(result), 1L)
  expect_equal(result[[1]]$id, PEDIGREE_ID)
  expect_equal(rec$state$calls[[1]]$method, "GET")
  expect_equal(rec$state$calls[[1]]$url, paste0(BASE_URL, "/api/pedigrees"))
  expect_equal(unname(rec$state$calls[[1]]$headers[["X-API-Key"]]), "evg_test")
})

# ----------------------------------------------------------- run_risk

test_that("run_risk posts model and extra body fields", {
  rec <- scripted_gateway(list(response(200, list(cancer_risk = list()))))
  client <- build_client(rec$gateway)

  client$run_risk(
    PEDIGREE_ID, "TYRER_CUZICK",
    extra = list(age_at_menarche = 12L, parity = 0L)
  )

  call <- rec$state$calls[[1]]
  expect_equal(call$method, "POST")
  expect_equal(call$url, sprintf("%s/api/pedigrees/%s/risk/calculate", BASE_URL, PEDIGREE_ID))
  body <- jsonlite::fromJSON(call$body_json, simplifyVector = FALSE)
  expect_equal(body$model, "TYRER_CUZICK")
  expect_equal(body$age_at_menarche, 12)
  expect_equal(body$parity, 0)
})

test_that("run_risk raises api_error on non-2xx", {
  rec <- scripted_gateway(list(response(500, list())))
  client <- build_client(rec$gateway)

  expect_error(client$run_risk(PEDIGREE_ID, "NICE"), class = "api_error")
})

# ----------------------------------------------------------- clone sequence

test_that("clone_pedigree_for_exploration sequences export / create / import", {
  rec <- scripted_gateway(list(
    response(200, text = "0 HEAD\n0 TRLR\n"),
    response(201, list(id = SCRATCH_ID)),
    response(204, list())
  ))
  client <- build_client(rec$gateway)

  scratch_id <- client$clone_pedigree_for_exploration(PEDIGREE_ID, "2026-04-20 12:00")

  expect_equal(scratch_id, SCRATCH_ID)
  expect_equal(length(rec$state$calls), 3L)
  expect_equal(rec$state$calls[[1]]$method, "GET")
  expect_equal(
    rec$state$calls[[1]]$url,
    sprintf("%s/api/pedigrees/%s/export.ged", BASE_URL, PEDIGREE_ID)
  )
  expect_equal(rec$state$calls[[2]]$method, "POST")
  expect_equal(rec$state$calls[[2]]$url, paste0(BASE_URL, "/api/pedigrees"))
  create_body <- jsonlite::fromJSON(rec$state$calls[[2]]$body_json, simplifyVector = FALSE)
  expect_true(startsWith(create_body$display_name, "[scratch] notebook-explorer"))

  expect_equal(rec$state$calls[[3]]$method, "POST")
  expect_equal(
    rec$state$calls[[3]]$url,
    sprintf("%s/api/pedigrees/%s/import/gedcom", BASE_URL, SCRATCH_ID)
  )
  import_body <- jsonlite::fromJSON(rec$state$calls[[3]]$body_json, simplifyVector = FALSE)
  expect_equal(import_body$content, "0 HEAD\n0 TRLR\n")
})

test_that("clone_pedigree_for_exploration rejects create without id", {
  rec <- scripted_gateway(list(
    response(200, text = "0 HEAD\n0 TRLR\n"),
    response(201, list(name = "no id"))
  ))
  client <- build_client(rec$gateway)

  expect_error(
    client$clone_pedigree_for_exploration(PEDIGREE_ID, "2026-04-20 12:00"),
    class = "api_error"
  )
})

# ----------------------------------------------------------- delete + mutate

test_that("delete_pedigree issues DELETE", {
  rec <- scripted_gateway(list(response(204, list())))
  build_client(rec$gateway)$delete_pedigree(SCRATCH_ID)

  expect_equal(rec$state$calls[[1]]$method, "DELETE")
  expect_equal(
    rec$state$calls[[1]]$url,
    sprintf("%s/api/pedigrees/%s", BASE_URL, SCRATCH_ID)
  )
})

test_that("add_relative posts to register endpoint", {
  rec <- scripted_gateway(list(response(200, list(individual = list(id = RELATIVE_ID)))))
  client <- build_client(rec$gateway)

  result <- client$add_relative(
    SCRATCH_ID,
    relative_of = INDIVIDUAL_ID,
    relative_type = "sister",
    display_name = "Scratch sister",
    biological_sex = "female"
  )

  expect_equal(result$individual$id, RELATIVE_ID)
  call <- rec$state$calls[[1]]
  expect_equal(
    call$url,
    sprintf("%s/api/pedigrees/%s/register/add-relative", BASE_URL, SCRATCH_ID)
  )
  body <- jsonlite::fromJSON(call$body_json, simplifyVector = FALSE)
  expect_equal(body$relative_type, "sister")
  expect_equal(body$biological_sex, "female")
})

test_that("add_disease_to_individual posts affection and age", {
  rec <- scripted_gateway(list(response(201, list())))
  build_client(rec$gateway)$add_disease_to_individual(
    RELATIVE_ID, disease_id = DISEASE_ID, age_at_diagnosis = 42L
  )

  call <- rec$state$calls[[1]]
  expect_equal(call$url, sprintf("%s/api/individuals/%s/diseases", BASE_URL, RELATIVE_ID))
  body <- jsonlite::fromJSON(call$body_json, simplifyVector = FALSE)
  expect_equal(body$disease_id, DISEASE_ID)
  expect_equal(body$affection_status, "affected")
  expect_equal(body$age_at_diagnosis, 42)
})

test_that("patch_individual PATCHes the individual with arbitrary fields", {
  rec <- scripted_gateway(list(response(200, list())))
  build_client(rec$gateway)$patch_individual(
    INDIVIDUAL_ID,
    fields = list(age_at_menarche = 12L, parity = 2L, breast_density_birads = 3L)
  )

  call <- rec$state$calls[[1]]
  expect_equal(call$method, "PATCH")
  expect_equal(call$url, sprintf("%s/api/individuals/%s", BASE_URL, INDIVIDUAL_ID))
  body <- jsonlite::fromJSON(call$body_json, simplifyVector = FALSE)
  expect_equal(body$age_at_menarche, 12)
  expect_equal(body$parity, 2)
  expect_equal(body$breast_density_birads, 3)
})

test_that("get_register returns server object", {
  rec <- scripted_gateway(list(response(200, list(proband_id = INDIVIDUAL_ID, rows = list()))))
  result <- build_client(rec$gateway)$get_register(SCRATCH_ID)

  expect_equal(result$proband_id, INDIVIDUAL_ID)
  call <- rec$state$calls[[1]]
  expect_equal(call$method, "GET")
  expect_equal(
    call$url,
    sprintf("%s/api/pedigrees/%s/register", BASE_URL, SCRATCH_ID)
  )
})

# ----------------------------------------------------------- evagene_url

test_that("evagene_url is credential free", {
  rec <- scripted_gateway(list())
  url <- build_client(rec$gateway)$evagene_url(PEDIGREE_ID)

  expect_equal(url, sprintf("%s/pedigrees/%s", BASE_URL, PEDIGREE_ID))
  expect_false(grepl("evg_", url))
})
