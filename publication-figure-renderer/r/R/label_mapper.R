# Pure transform: (pedigree_detail, label_style) -> named list of
# individual_id -> new_label.  Labels here are what we *want* the SVG
# text nodes to read; the SVG deidentifier applies them by original
# name.
#
# Strict on schema -- a silent default would mask a server-side change
# and leave callers reasoning over stale labels.

UNKNOWN_GENERATION <- "?"

#' Build an individual_id -> new_label mapping in the requested style.
#'
#' @param detail A parsed PedigreeDetail (e.g. from `fetch_pedigree_detail`).
#' @param label_style One of "initials", "generation-number", "off".
#' @return A named character vector: names are individual IDs, values are
#'   the replacement labels.  An "off" style returns empty strings.
build_label_mapping <- function(detail, label_style) {
  individuals <- require_individuals(detail)

  strategy <- label_strategy(label_style)
  mapping <- strategy(individuals)

  ids <- vapply(individuals, function(ind) require_id(ind), character(1L))
  stats::setNames(mapping, ids)
}

# --- Strategies -----------------------------------------------------------

label_strategy <- function(label_style) {
  switch(label_style,
    `off` = label_blank,
    `initials` = label_initials,
    `generation-number` = label_generation_number,
    stop(sprintf("Unknown label style: %s", label_style))
  )
}

label_blank <- function(individuals) {
  rep("", length(individuals))
}

label_initials <- function(individuals) {
  vapply(individuals, function(ind) initials_of(optional_string(ind, "display_name")),
         character(1L))
}

label_generation_number <- function(individuals) {
  # Prefer the explicit `generation` field; fall back on the vertical
  # layout coordinate (smaller y = higher up the page = earlier
  # generation).  Individuals with neither fall back to "?-n".
  keys <- lapply(individuals, generation_key)
  key_strings <- vapply(keys, function(key) {
    if (is.null(key)) NA_character_ else paste0(key[[1L]], ":", key[[2L]])
  }, character(1L))

  known <- key_strings[!is.na(key_strings)]
  ordered_unique <- unique(known[order(vapply(known, key_source, integer(1L)),
                                       vapply(known, key_value, numeric(1L)))])
  roman_of <- stats::setNames(
    vapply(seq_along(ordered_unique), integer_to_roman, character(1L)),
    ordered_unique
  )

  counts <- rep(0L, length(ordered_unique))
  names(counts) <- ordered_unique

  out <- character(length(individuals))
  unknown_index <- 0L
  for (i in seq_along(individuals)) {
    key <- key_strings[[i]]
    if (is.na(key)) {
      unknown_index <- unknown_index + 1L
      out[[i]] <- sprintf("%s-%d", UNKNOWN_GENERATION, unknown_index)
    } else {
      counts[[key]] <- counts[[key]] + 1L
      out[[i]] <- sprintf("%s-%d", roman_of[[key]], counts[[key]])
    }
  }
  out
}

key_source <- function(key_string) {
  as.integer(strsplit(key_string, ":", fixed = TRUE)[[1L]][[1L]])
}

key_value <- function(key_string) {
  as.numeric(strsplit(key_string, ":", fixed = TRUE)[[1L]][[2L]])
}

# --- Helpers --------------------------------------------------------------

initials_of <- function(name) {
  if (!nzchar(name)) {
    return("")
  }
  tokens <- strsplit(name, "\\s+", perl = TRUE)[[1L]]
  tokens <- tokens[nzchar(tokens)]
  letters <- vapply(tokens, function(token) substr(token, 1L, 1L), character(1L))
  toupper(paste(letters, collapse = ""))
}

integer_to_roman <- function(index) {
  # Package-only dependence on base R: `utils::as.roman()` handles 1..3999.
  as.character(utils::as.roman(index))
}

generation_key <- function(individual) {
  # Two-part key: priority tag + numeric value.  Priority 0 = explicit
  # generation field, priority 1 = inferred from y-coordinate layout.
  generation <- individual[["generation"]]
  if (is_single_number(generation)) {
    return(c(0L, as.numeric(generation)))
  }
  y <- individual[["y"]]
  if (is_single_number(y)) {
    return(c(1L, as.numeric(y)))
  }
  NULL
}

is_single_number <- function(value) {
  is.numeric(value) && length(value) == 1L && !is.na(value) && !is.logical(value)
}

require_individuals <- function(detail) {
  individuals <- detail[["individuals"]]
  if (is.null(individuals)) {
    return(list())
  }
  if (!is.list(individuals)) {
    stop(sprintf("detail$individuals is not a list"))
  }
  individuals
}

require_id <- function(individual) {
  id <- individual[["id"]]
  if (!is.character(id) || length(id) != 1L || is.na(id) || !nzchar(id)) {
    stop("individual is missing a string 'id' field")
  }
  id
}

optional_string <- function(container, key) {
  value <- container[[key]]
  if (!is.character(value) || length(value) != 1L || is.na(value)) {
    return("")
  }
  value
}
