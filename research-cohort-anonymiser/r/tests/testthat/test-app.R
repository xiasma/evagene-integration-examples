make_recording_client <- function() {
  state <- new.env(parent = emptyenv())
  state$calls <- list()
  state$counter <- 0L
  issue_id <- function() {
    state$counter <- state$counter + 1L
    sprintf("id-%04d", state$counter)
  }
  record <- function(op, payload) {
    state$calls[[length(state$calls) + 1L]] <- list(op = op, payload = payload)
  }
  client <- list()
  client$create_pedigree <- function(display_name) {
    new_id <- issue_id()
    record("create_pedigree", list(display_name = display_name, returned = new_id))
    new_id
  }
  client$create_individual <- function(display_name, biological_sex) {
    new_id <- issue_id()
    record("create_individual", list(display_name = display_name,
                                     biological_sex = biological_sex,
                                     returned = new_id))
    new_id
  }
  client$add_individual_to_pedigree <- function(pedigree_id, individual_id) {
    record("add_individual_to_pedigree",
           list(pedigree_id = pedigree_id, individual_id = individual_id))
  }
  client$designate_as_proband <- function(individual_id) {
    record("designate_as_proband", list(individual_id = individual_id))
  }
  client$add_relative <- function(pedigree_id, relative_of, relative_type,
                                  display_name, biological_sex) {
    new_id <- issue_id()
    record("add_relative", list(pedigree_id = pedigree_id,
                                relative_of = relative_of,
                                relative_type = relative_type,
                                display_name = display_name,
                                biological_sex = biological_sex,
                                returned = new_id))
    new_id
  }
  client$rebuild_pedigree <- function(anonymised) {
    rebuild_pedigree(client, anonymised)
  }
  attr(client, "state") <- state
  client
}

test_that("rebuild sequence mirrors the intake-form demo", {
  anonymised <- load_fixture("expected-anonymised")
  client <- make_recording_client()

  new_pedigree_id <- client$rebuild_pedigree(anonymised)
  state <- attr(client, "state")
  ops <- vapply(state$calls, function(call) call$op, character(1L))

  expect_equal(ops[1L:4L], c(
    "create_pedigree",
    "create_individual",
    "add_individual_to_pedigree",
    "designate_as_proband"
  ))
  expect_true(all(ops[-c(1L:4L)] == "add_relative"))
  expect_match(new_pedigree_id, "^id-")
})

test_that("proband is created with anonymised display name, not a source name", {
  anonymised <- load_fixture("expected-anonymised")
  client <- make_recording_client()

  client$rebuild_pedigree(anonymised)
  state <- attr(client, "state")
  proband_call <- Filter(function(call) call$op == "create_individual", state$calls)[[1L]]

  expect_equal(proband_call$payload$display_name, "III-1")
  expect_equal(proband_call$payload$biological_sex, "female")
})

test_that("relatives are added with sex-derived relative types", {
  anonymised <- load_fixture("expected-anonymised")
  client <- make_recording_client()

  client$rebuild_pedigree(anonymised)
  state <- attr(client, "state")
  relative_types <- vapply(
    Filter(function(call) call$op == "add_relative", state$calls),
    function(call) call$payload$relative_type,
    character(1L)
  )

  expect_true("mother" %in% relative_types)
  expect_true("father" %in% relative_types)
  expect_true("brother" %in% relative_types)
})

test_that("app_run writes anonymised JSON to stdout given a fake client", {
  pedigree <- load_fixture("source-pedigree")
  fake_client <- list(
    get_pedigree_detail = function(pedigree_id) pedigree,
    rebuild_pedigree = function(anonymised) stop("should not be called")
  )
  out <- textConnection("out_capture", "w", local = TRUE)
  on.exit(close(out), add = TRUE)
  err <- textConnection("err_capture", "w", local = TRUE)
  on.exit(close(err), add = TRUE)

  exit_code <- app_run(
    c("a1cfe665-0000-4000-8000-000000000001"),
    list(EVAGENE_API_KEY = "evg_test"),
    out_sink = out,
    err_sink = err,
    client = fake_client
  )

  expect_equal(exit_code, EXIT_OK)
  rendered <- paste(textConnectionValue(out), collapse = "\n")
  expect_match(rendered, "\"display_name\": \"Anonymised pedigree\"")
  expect_match(rendered, "\"k_anonymity\":")
})
