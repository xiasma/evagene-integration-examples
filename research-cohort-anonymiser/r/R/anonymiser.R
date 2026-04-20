# Pure transform: PedigreeDetail + Rules -> AnonymisedPedigree.
#
# Each anonymisation rule is a small helper so tests can exercise it
# in isolation.  The orchestrating anonymise() is a straight-line
# composition; no branching beyond what the rules require.

FREE_TEXT_KEY_FRAGMENTS <- c("note", "comment", "description")
PEDIGREE_SCRUB_KEYS <- c("owner", "owner_name")
SEX_UNKNOWN <- "unknown"

#' Run the full anonymisation pipeline over a pedigree.
#'
#' @param pedigree A PedigreeDetail-shaped named list.
#' @param labels Named character vector: individual_id -> generation label.
#' @param rules Named list with `age_precision` and `keep_sex`.
#' @return An anonymised pedigree list (still ordered by generation).
anonymise_pedigree <- function(pedigree, labels, rules) {
  identifiers <- build_stable_identifiers(labels, pedigree$individuals)
  result <- list(
    display_name = anonymise_pedigree_display_name(pedigree$display_name %||% ""),
    date_represented = truncate_date(pedigree$date_represented, rules$age_precision),
    properties = strip_free_text_properties(pedigree$properties %||% list()),
    individuals = lapply(pedigree$individuals, function(individual) {
      anonymise_individual(individual, identifiers[[individual$id]], rules)
    }),
    relationships = lapply(pedigree$relationships %||% list(), anonymise_relationship),
    eggs = lapply(pedigree$eggs %||% list(), anonymise_egg)
  )
  for (key in PEDIGREE_SCRUB_KEYS) {
    if (key %in% names(pedigree)) {
      result[[key]] <- ""
    }
  }
  result
}

build_stable_identifiers <- function(labels, individuals) {
  by_label <- list()
  for (individual in individuals) {
    label <- labels[[individual$id]]
    by_label[[label]] <- c(by_label[[label]] %||% character(0L), individual$id)
  }
  identifiers <- character(0L)
  for (label in names(by_label)) {
    ids <- sort(by_label[[label]])
    for (i in seq_along(ids)) {
      identifiers[[ids[[i]]]] <- sprintf("%s-%d", label, i)
    }
  }
  identifiers
}

anonymise_individual <- function(individual, stable_id, rules) {
  list(
    id = individual$id,
    display_name = stable_id,
    generation_label = sub("-[^-]+$", "", stable_id),
    biological_sex = redact_sex(individual$biological_sex %||% "", rules$keep_sex),
    proband = individual$proband %||% 0L,
    proband_text = if (isTRUE(as.logical(individual$proband %||% 0L) != FALSE) &&
                         (individual$proband %||% 0L) != 0L) "P" else "",
    events = lapply(individual$events %||% list(), function(event) {
      anonymise_event(event, rules$age_precision)
    }),
    diseases = lapply(individual$diseases %||% list(), anonymise_disease),
    properties = strip_free_text_properties(individual$properties %||% list())
  )
}

anonymise_event <- function(event, precision) {
  list(
    type = event$type %||% "",
    date_start = truncate_date(event$date_start, precision),
    date_end = truncate_date(event$date_end, precision),
    properties = round_numeric_ages(
      strip_free_text_properties(event$properties %||% list()),
      precision
    )
  )
}

anonymise_disease <- function(disease) {
  list(
    disease_id = disease$disease_id %||% "",
    affection_status = disease$affection_status %||% "",
    manifestations = lapply(disease$manifestations %||% list(), anonymise_manifestation)
  )
}

anonymise_manifestation <- function(manifestation) {
  kept_keys <- setdiff(
    names(manifestation),
    c("display_name", names(manifestation)[vapply(names(manifestation),
                                                  is_free_text_key,
                                                  logical(1L))])
  )
  manifestation[kept_keys]
}

anonymise_relationship <- function(relationship) {
  list(
    id = relationship$id %||% "",
    members = unlist(relationship$members %||% list(), use.names = FALSE),
    consanguinity = relationship$consanguinity,
    consanguinity_override = relationship$consanguinity_override %||% FALSE,
    properties = strip_free_text_properties(relationship$properties %||% list())
  )
}

anonymise_egg <- function(egg) {
  list(
    id = egg$id %||% "",
    individual_id = egg$individual_id,
    individual_ids = unlist(egg$individual_ids %||% list(), use.names = FALSE),
    relationship_id = egg$relationship_id,
    adopted = egg$adopted %||% FALSE,
    fostered = egg$fostered %||% FALSE
  )
}

anonymise_pedigree_display_name <- function(raw) {
  if (nzchar(raw)) "Anonymised pedigree" else ""
}

redact_sex <- function(raw, keep_sex) {
  if (keep_sex) raw else SEX_UNKNOWN
}

strip_free_text_properties <- function(properties) {
  keep <- !vapply(names(properties), is_free_text_key, logical(1L))
  properties[keep]
}

is_free_text_key <- function(key) {
  lowered <- tolower(key)
  any(vapply(FREE_TEXT_KEY_FRAGMENTS, function(fragment) grepl(fragment, lowered, fixed = TRUE),
             logical(1L)))
}

truncate_date <- function(raw, precision) {
  if (is.null(raw) || !nzchar(raw)) {
    return(raw)
  }
  parsed <- tryCatch(
    suppressWarnings(as.Date(substr(raw, 1L, 10L), format = "%Y-%m-%d")),
    error = function(e) as.Date(NA)
  )
  if (is.na(parsed)) {
    return(NA_character_)
  }
  year <- as.integer(format(parsed, "%Y"))
  bucket <- bucket_size(precision)
  bucketed_year <- if (bucket > 1L) (year %/% bucket) * bucket else year
  sprintf("%04d-01-01", bucketed_year)
}

round_age <- function(age, precision) {
  bucket <- bucket_size(precision)
  (age %/% bucket) * bucket
}

round_numeric_ages <- function(properties, precision) {
  result <- properties
  for (key in names(properties)) {
    value <- properties[[key]]
    if (grepl("age", tolower(key), fixed = TRUE) &&
        is.numeric(value) && length(value) == 1L && !is.logical(value)) {
      result[[key]] <- round_age(as.integer(value), precision)
    }
  }
  result
}

bucket_size <- function(precision) {
  switch(precision,
    "year" = 1L,
    "five-year" = 5L,
    "decade" = 10L,
    stop(sprintf("Unknown age precision: %s", precision))
  )
}
