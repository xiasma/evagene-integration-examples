# End-to-end workflow: upload two partners, fetch risks, combine, clean up.
#
# The orchestrator owns the lifetime of the scratch pedigree and
# individuals.  Cleanup runs on.exit so a half-built workspace never
# lingers on the user's account even when an import fails mid-run.

SCRATCH_PEDIGREE_NAME <- "couple-carrier-risk scratch"

#' Raise an ancestry_not_found_error condition.
#' @noRd
stop_ancestry_not_found <- function(message) {
  stop(structure(
    list(message = message, call = sys.call(-1)),
    class = c("ancestry_not_found_error", "error", "condition")
  ))
}

#' Run the couple-carrier-risk workflow end-to-end.
#'
#' @param config Named list from `load_config()`.
#' @param client Named list of bound Evagene client functions
#'   (see `make_evagene_client()`), so tests can substitute fakes.
#' @param sink Writable connection for the rendered table.
run_couple_screening <- function(config, client, sink) {
  partners <- load_partners(config)
  pedigree_id <- client$create_pedigree(SCRATCH_PEDIGREE_NAME)
  created <- character(0)
  on.exit(cleanup(client, pedigree_id, created, config$cleanup), add = TRUE)

  partner_risks <- list()
  for (partner in partners) {
    individual_id <- onboard_partner(client, pedigree_id, partner)
    created <- c(created, individual_id)
    partner_risks[[length(partner_risks) + 1L]] <- list(
      biological_sex = partner$genome$biological_sex,
      risks = parse_population_risks(client$get_population_risks(individual_id))
    )
  }

  rows <- build_couple_rows(partner_risks[[1L]], partner_risks[[2L]])
  presenter_for(config$output)(rows, sink)
  invisible(NULL)
}

load_partners <- function(config) {
  list(
    list(
      display_name = "Partner A",
      genome = load_genome_file(config$partner_a_file),
      ancestry = config$ancestry_a
    ),
    list(
      display_name = "Partner B",
      genome = load_genome_file(config$partner_b_file),
      ancestry = config$ancestry_b
    )
  )
}

onboard_partner <- function(client, pedigree_id, partner) {
  individual_id <- client$create_individual(
    display_name = partner$display_name,
    biological_sex = partner$genome$biological_sex
  )
  client$add_individual_to_pedigree(pedigree_id, individual_id)
  record_ancestry_if_explicit(client, individual_id, partner$ancestry)
  client$import_23andme_raw(pedigree_id, individual_id, partner$genome$content)
  individual_id
}

#' Attach the named ancestry (proportion 1.0) when the caller specifies one.
#'
#' AUTO_ANCESTRY ("auto") defers to Evagene's own ancestry inference.
#' An unknown population key surfaces as an error -- silent fallback
#' would hide a typo that produces subtly wrong carrier frequencies.
record_ancestry_if_explicit <- function(client, individual_id, ancestry) {
  if (identical(ancestry, AUTO_ANCESTRY)) {
    return(invisible(NULL))
  }
  ancestry_id <- client$find_ancestry_id_by_population_key(ancestry)
  if (is.null(ancestry_id)) {
    stop_ancestry_not_found(sprintf(
      paste0("No ancestry in the Evagene catalogue has population_key='%s'. ",
             "List available keys at GET /api/ancestries or pass --ancestry-a auto."),
      ancestry
    ))
  }
  client$add_ancestry_to_individual(individual_id, ancestry_id)
}

cleanup <- function(client, pedigree_id, individual_ids, enabled) {
  if (!isTRUE(enabled)) {
    return(invisible(NULL))
  }
  for (individual_id in individual_ids) {
    try(client$delete_individual(individual_id), silent = TRUE)
  }
  try(client$delete_pedigree(pedigree_id), silent = TRUE)
  invisible(NULL)
}

#' Bind the low-level Evagene client functions to a gateway + base_url + api_key.
#'
#' Returns a named list of nullary / minimal-argument functions that
#' the orchestrator uses.  Keeps the orchestrator free of transport
#' concerns.
make_evagene_client <- function(gateway, base_url, api_key) {
  list(
    create_pedigree = function(display_name) {
      create_pedigree(gateway, base_url, api_key, display_name)
    },
    delete_pedigree = function(pedigree_id) {
      delete_pedigree(gateway, base_url, api_key, pedigree_id)
    },
    add_individual_to_pedigree = function(pedigree_id, individual_id) {
      add_individual_to_pedigree(gateway, base_url, api_key, pedigree_id, individual_id)
    },
    create_individual = function(display_name, biological_sex) {
      create_individual(gateway, base_url, api_key, display_name, biological_sex)
    },
    delete_individual = function(individual_id) {
      delete_individual(gateway, base_url, api_key, individual_id)
    },
    import_23andme_raw = function(pedigree_id, individual_id, tsv) {
      import_23andme_raw(gateway, base_url, api_key, pedigree_id, individual_id, tsv)
    },
    find_ancestry_id_by_population_key = function(population_key) {
      find_ancestry_id_by_population_key(gateway, base_url, api_key, population_key)
    },
    add_ancestry_to_individual = function(individual_id, ancestry_id) {
      add_ancestry_to_individual(gateway, base_url, api_key, individual_id, ancestry_id)
    },
    get_population_risks = function(individual_id) {
      get_population_risks(gateway, base_url, api_key, individual_id)
    }
  )
}
