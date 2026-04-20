# Serialise an anonymised pedigree and its k-anonymity estimate as JSON.
#
# Deterministic key ordering matches the Python presenter so both
# languages emit byte-identical output for the same input.

INDIVIDUAL_KEY_ORDER <- c(
  "id", "display_name", "generation_label", "biological_sex",
  "proband", "proband_text", "events", "diseases", "properties"
)
EVENT_KEY_ORDER <- c("type", "date_start", "date_end", "properties")
DISEASE_KEY_ORDER <- c("disease_id", "affection_status", "manifestations")
RELATIONSHIP_KEY_ORDER <- c(
  "id", "members", "consanguinity", "consanguinity_override", "properties"
)
EGG_KEY_ORDER <- c(
  "id", "individual_id", "individual_ids", "relationship_id", "adopted", "fostered"
)
TOP_LEVEL_KEY_ORDER <- c(
  "display_name", "date_represented", "properties",
  "individuals", "relationships", "eggs", "k_anonymity"
)

#' Render an anonymised pedigree + estimate as diff-friendly JSON.
#'
#' @param anonymised List returned by `anonymise_pedigree()`.
#' @param estimate   List returned by `estimate_k_anonymity()`.
#' @return Character scalar (JSON with trailing newline).
render_json <- function(anonymised, estimate) {
  document <- list(
    display_name = anonymised$display_name %||% "",
    date_represented = anonymised$date_represented,
    properties = anonymised$properties %||% list(),
    individuals = lapply(anonymised$individuals %||% list(), function(individual) {
      ordered <- ordered_list(individual, INDIVIDUAL_KEY_ORDER)
      ordered$events <- lapply(ordered$events %||% list(),
                               function(event) ordered_list(event, EVENT_KEY_ORDER))
      ordered$diseases <- lapply(ordered$diseases %||% list(),
                                 function(disease) ordered_list(disease, DISEASE_KEY_ORDER))
      ordered
    }),
    relationships = lapply(anonymised$relationships %||% list(),
                           function(rel) ordered_list(rel, RELATIONSHIP_KEY_ORDER)),
    eggs = lapply(anonymised$eggs %||% list(),
                  function(egg) ordered_list(egg, EGG_KEY_ORDER)),
    k_anonymity = render_estimate(estimate)
  )
  ordered <- document[intersect(TOP_LEVEL_KEY_ORDER, names(document))]
  text <- jsonlite::toJSON(ordered, pretty = 2L, auto_unbox = TRUE, null = "null")
  paste0(text, "\n")
}

render_estimate <- function(estimate) {
  list(
    k = estimate$k,
    bucket_count = estimate$bucket_count,
    smallest_bucket_key = estimate$smallest_bucket_key,
    total_individuals = estimate$total_individuals
  )
}

ordered_list <- function(record, key_order) {
  record[intersect(key_order, names(record))]
}
