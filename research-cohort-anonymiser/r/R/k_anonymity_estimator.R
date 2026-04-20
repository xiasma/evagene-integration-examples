# Estimate k-anonymity over a simple quasi-identifier bucketing.
#
# Buckets are (biological_sex, birth-year, disease-count).  Deliberately
# coarse.  The README is honest about what this measure is and is not.

UNKNOWN_YEAR <- "unknown"

#' Estimate k-anonymity for an anonymised pedigree.
#'
#' @param anonymised A pedigree returned by `anonymise_pedigree()`.
#' @return Named list with `k`, `bucket_count`, `smallest_bucket_key`,
#'   `total_individuals`.
estimate_k_anonymity <- function(anonymised) {
  individuals <- anonymised$individuals %||% list()
  if (length(individuals) == 0L) {
    return(list(k = 0L, bucket_count = 0L, smallest_bucket_key = NULL, total_individuals = 0L))
  }

  keys <- lapply(individuals, bucket_key)
  key_strings <- vapply(keys, paste, character(1L), collapse = "\x1f")
  counts <- table(key_strings)

  smallest_size <- min(counts)
  smallest_name <- names(counts)[which.min(counts)]
  smallest_key_parts <- keys[[which(key_strings == smallest_name)[[1L]]]]

  list(
    k = unname(as.integer(smallest_size)),
    bucket_count = length(counts),
    smallest_bucket_key = smallest_key_parts,
    total_individuals = length(individuals)
  )
}

bucket_key <- function(individual) {
  c(
    sex_bucket(individual$biological_sex %||% ""),
    year_bucket(individual$events %||% list()),
    as.character(disease_count(individual$diseases %||% list()))
  )
}

sex_bucket <- function(raw) {
  if (nzchar(raw)) raw else "unknown"
}

year_bucket <- function(events) {
  for (event in events) {
    if (identical(event$type, "birth")) {
      date_start <- event$date_start
      if (is.character(date_start) && nchar(date_start) >= 4L) {
        return(substr(date_start, 1L, 4L))
      }
    }
  }
  UNKNOWN_YEAR
}

disease_count <- function(diseases) {
  sum(vapply(
    diseases,
    function(disease) identical(disease$affection_status, "affected"),
    logical(1L)
  ))
}
