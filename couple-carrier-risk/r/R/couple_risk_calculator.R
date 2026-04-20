# Pure transform: two population-risk payloads -> a per-disease couple table.
#
# The Evagene API already returns `couple_offspring_risk` per row, but
# that figure assumes a same-ancestry, untested partner.  When both
# partners' carrier frequencies are known we compute a genuinely
# cross-partner value:
#
#   AR:  cf_a * cf_b / 4
#   XLR: cf_female / 4
#
# Single-partner rows (disease present in only one response) carry
# through with a NULL cross-partner figure rather than a fabricated one.

INHERITANCE_AR <- "autosomal_recessive"
INHERITANCE_XLR <- "x_linked_recessive"

#' Raise a response_schema_error condition.
#' @noRd
stop_schema <- function(message) {
  stop(structure(
    list(message = message, call = sys.call(-1)),
    class = c("response_schema_error", "error", "condition")
  ))
}

#' Parse a population-risks response into a disease-name-keyed list of rows.
#'
#' @param payload Parsed JSON (named list with `risks` array).
#' @return A named list where each element is the API row for that disease.
parse_population_risks <- function(payload) {
  risks <- payload$risks
  if (!is.list(risks)) {
    stop_schema("population-risks response lacks a 'risks' list")
  }
  indexed <- list()
  for (entry in risks) {
    if (!is.list(entry)) {
      stop_schema(sprintf("population-risks 'risks[]' entry is not an object: %s", entry))
    }
    disease_name <- entry$disease_name
    if (!is.character(disease_name) || length(disease_name) != 1L || !nzchar(disease_name)) {
      stop_schema("population-risks row lacks a string 'disease_name'")
    }
    indexed[[disease_name]] <- entry
  }
  indexed
}

#' Combine two PartnerRisks into one CoupleRow per disease.
#'
#' @param partner_a A list with fields `biological_sex` and `risks`
#'   (named list keyed by disease_name).
#' @param partner_b Same shape as `partner_a`.
#' @return A list of `couple_row` lists with fields disease_name,
#'   inheritance_pattern, carrier_frequency_a, carrier_frequency_b,
#'   api_couple_offspring_risk_a, api_couple_offspring_risk_b,
#'   cross_partner_offspring_risk.
build_couple_rows <- function(partner_a, partner_b) {
  disease_names <- union_preserving_order(names(partner_a$risks), names(partner_b$risks))
  lapply(disease_names, function(disease_name) {
    build_row(partner_a, partner_b, disease_name)
  })
}

build_row <- function(partner_a, partner_b, disease_name) {
  row_a <- partner_a$risks[[disease_name]]
  row_b <- partner_b$risks[[disease_name]]
  inheritance <- inheritance_of(row_a, row_b)

  cf_a <- number_or_null(row_a, "carrier_frequency")
  cf_b <- number_or_null(row_b, "carrier_frequency")

  structure(
    list(
      disease_name = disease_name,
      inheritance_pattern = inheritance,
      carrier_frequency_a = cf_a,
      carrier_frequency_b = cf_b,
      api_couple_offspring_risk_a = number_or_null(row_a, "couple_offspring_risk"),
      api_couple_offspring_risk_b = number_or_null(row_b, "couple_offspring_risk"),
      cross_partner_offspring_risk = cross_partner_risk(
        inheritance,
        cf_a = cf_a, cf_b = cf_b,
        biological_sex_a = partner_a$biological_sex,
        biological_sex_b = partner_b$biological_sex
      )
    ),
    class = "couple_row"
  )
}

cross_partner_risk <- function(inheritance, cf_a, cf_b,
                               biological_sex_a, biological_sex_b) {
  if (inheritance == INHERITANCE_AR) {
    if (is.null(cf_a) || is.null(cf_b)) return(NULL)
    return(cf_a * cf_b / 4)
  }
  if (inheritance == INHERITANCE_XLR) {
    cf_female <- female_carrier_frequency(
      cf_a, cf_b, biological_sex_a, biological_sex_b
    )
    if (is.null(cf_female)) return(NULL)
    return(cf_female / 4)
  }
  NULL
}

female_carrier_frequency <- function(cf_a, cf_b, biological_sex_a, biological_sex_b) {
  if (identical(biological_sex_a, SEX_FEMALE)) return(cf_a)
  if (identical(biological_sex_b, SEX_FEMALE)) return(cf_b)
  NULL
}

inheritance_of <- function(row_a, row_b) {
  for (row in list(row_a, row_b)) {
    if (is.null(row)) next
    pattern <- row$inheritance_pattern
    if (is.character(pattern) && length(pattern) == 1L && nzchar(pattern)) {
      return(pattern)
    }
  }
  stop_schema("population-risks row lacks a string 'inheritance_pattern'")
}

number_or_null <- function(row, key) {
  if (is.null(row)) return(NULL)
  value <- row[[key]]
  if (is.null(value)) return(NULL)
  if (!is.numeric(value) || length(value) != 1L || is.na(value)) {
    stop_schema(sprintf("population-risks field '%s' is not a number", key))
  }
  as.numeric(value)
}

union_preserving_order <- function(first, second) {
  c(first, setdiff(second, first))
}
