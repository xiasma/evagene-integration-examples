make_fake_client <- function() {
  state <- new.env(parent = emptyenv())
  state$next_id <- 0L
  state$created_pedigrees <- character(0)
  state$created_individuals <- list()
  state$memberships <- list()
  state$imported <- list()
  state$deleted_pedigrees <- character(0)
  state$deleted_individuals <- character(0)
  state$recorded_ancestries <- list()
  state$ancestry_lookup <- list()
  state$get_population_risks <- NULL

  fresh_id <- function(prefix) {
    state$next_id <- state$next_id + 1L
    sprintf("%s-%d", prefix, state$next_id)
  }

  client <- list(
    create_pedigree = function(display_name) {
      state$created_pedigrees <- c(state$created_pedigrees, display_name)
      fresh_id("ped")
    },
    delete_pedigree = function(pedigree_id) {
      state$deleted_pedigrees <- c(state$deleted_pedigrees, pedigree_id)
    },
    add_individual_to_pedigree = function(pedigree_id, individual_id) {
      state$memberships[[length(state$memberships) + 1L]] <- c(pedigree_id, individual_id)
    },
    create_individual = function(display_name, biological_sex) {
      identifier <- fresh_id("ind")
      state$created_individuals[[length(state$created_individuals) + 1L]] <- list(
        id = identifier,
        display_name = display_name,
        biological_sex = biological_sex
      )
      identifier
    },
    delete_individual = function(individual_id) {
      state$deleted_individuals <- c(state$deleted_individuals, individual_id)
    },
    import_23andme_raw = function(pedigree_id, individual_id, tsv) {
      state$imported[[length(state$imported) + 1L]] <- list(id = individual_id)
    },
    find_ancestry_id_by_population_key = function(population_key) {
      state$ancestry_lookup[[population_key]]
    },
    add_ancestry_to_individual = function(individual_id, ancestry_id) {
      state$recorded_ancestries[[length(state$recorded_ancestries) + 1L]] <-
        c(individual_id, ancestry_id)
    },
    get_population_risks = function(individual_id) {
      if (!is.null(state$get_population_risks)) {
        return(state$get_population_risks(individual_id))
      }
      list(
        individual_id = individual_id,
        risks = list(list(
          disease_id = "d1",
          disease_name = "Sickle cell anaemia",
          inheritance_pattern = "autosomal_recessive",
          carrier_frequency = 0.05,
          couple_offspring_risk = 0.000625
        ))
      )
    }
  )
  list(client = client, state = state)
}

test_config <- function(ancestry_a = "auto", ancestry_b = "auto", cleanup = TRUE) {
  list(
    base_url = "https://evagene.example",
    api_key = "evg_test",
    partner_a_file = fixture_path("partner-a-23andme.txt"),
    partner_b_file = fixture_path("partner-b-23andme.txt"),
    ancestry_a = ancestry_a,
    ancestry_b = ancestry_b,
    output = "table",
    cleanup = cleanup
  )
}

capture_output <- function(fn) {
  output <- character(0)
  sink_conn <- textConnection("output", "w", local = TRUE)
  on.exit(close(sink_conn), add = TRUE)
  fn(sink_conn)
  paste(output, collapse = "\n")
}

test_that("end-to-end happy path creates scratch and renders the table", {
  fake <- make_fake_client()

  output <- capture_output(function(sink) {
    run_couple_screening(test_config(), fake$client, sink)
  })

  expect_true(grepl("Sickle cell anaemia", output, fixed = TRUE))
  expect_equal(fake$state$created_pedigrees, SCRATCH_PEDIGREE_NAME)
  expect_equal(
    vapply(fake$state$created_individuals, function(ind) ind$display_name, character(1L)),
    c("Partner A", "Partner B")
  )
  expect_length(fake$state$imported, 2L)
})

test_that("cleanup deletes pedigree and individuals on success", {
  fake <- make_fake_client()

  capture_output(function(sink) {
    run_couple_screening(test_config(cleanup = TRUE), fake$client, sink)
  })

  expect_length(fake$state$deleted_individuals, 2L)
  expect_length(fake$state$deleted_pedigrees, 1L)
})

test_that("--no-cleanup leaves scratch in place", {
  fake <- make_fake_client()

  capture_output(function(sink) {
    run_couple_screening(test_config(cleanup = FALSE), fake$client, sink)
  })

  expect_length(fake$state$deleted_pedigrees, 0L)
  expect_length(fake$state$deleted_individuals, 0L)
})

test_that("cleanup runs even when risk fetch fails", {
  fake <- make_fake_client()
  fake$state$get_population_risks <- function(individual_id) {
    stop("network broke mid-run")
  }

  expect_error(
    capture_output(function(sink) {
      run_couple_screening(test_config(cleanup = TRUE), fake$client, sink)
    }),
    "network broke"
  )

  expect_gte(length(fake$state$deleted_pedigrees), 1L)
})

test_that("explicit ancestry is looked up and attached", {
  fake <- make_fake_client()
  fake$state$ancestry_lookup <- list(mediterranean = "anc-uuid")

  capture_output(function(sink) {
    run_couple_screening(
      test_config(ancestry_a = "mediterranean", ancestry_b = "mediterranean"),
      fake$client, sink
    )
  })

  expect_equal(
    vapply(fake$state$recorded_ancestries, function(entry) entry[[2L]], character(1L)),
    c("anc-uuid", "anc-uuid")
  )
})

test_that("unknown ancestry key raises ancestry_not_found_error", {
  fake <- make_fake_client()
  fake$state$ancestry_lookup <- list()

  expect_error(
    capture_output(function(sink) {
      run_couple_screening(
        test_config(ancestry_a = "klingon"), fake$client, sink
      )
    }),
    class = "ancestry_not_found_error"
  )
})
