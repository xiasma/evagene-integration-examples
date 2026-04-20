# Assign a generation label (I, II, III, ...) to every individual in a pedigree.
#
# Pure transform: a PedigreeDetail list in, a character vector named
# by individual ID out.  Derives generations from eggs + relationships;
# partners who would otherwise remain founders are pulled into their
# spouse's generation so pedigrees with in-laws behave sensibly.

UNKNOWN_GENERATION_LABEL <- "G?"

#' Assign a roman-numeral generation label to every individual.
#'
#' @param pedigree A PedigreeDetail-shaped named list.
#' @return A named character vector: names are individual IDs, values are labels.
assign_generation_labels <- function(pedigree) {
  individual_ids <- collect_individual_ids(pedigree)
  parents_of <- build_parent_map(pedigree)
  partners_of <- build_partner_map(pedigree)
  generations <- assign_generations(individual_ids, parents_of)
  generations <- align_partners(generations, partners_of)
  labels <- vapply(generations, label_for, character(1L))
  names(labels) <- names(generations)
  labels
}

collect_individual_ids <- function(pedigree) {
  vapply(pedigree$individuals, function(individual) individual$id, character(1L))
}

build_parent_map <- function(pedigree) {
  relationships_by_id <- list()
  for (relationship in pedigree$relationships %||% list()) {
    relationships_by_id[[relationship$id]] <- relationship
  }
  parents_of <- list()
  for (egg in pedigree$eggs %||% list()) {
    children <- children_of_egg(egg)
    parents <- parents_of_egg(egg, relationships_by_id)
    for (child in children) {
      parents_of[[child]] <- c(parents_of[[child]] %||% character(0L), parents)
    }
  }
  parents_of
}

children_of_egg <- function(egg) {
  multiple <- egg$individual_ids %||% list()
  if (length(multiple) > 0L) {
    return(unlist(multiple, use.names = FALSE))
  }
  if (!is.null(egg$individual_id)) {
    return(egg$individual_id)
  }
  character(0L)
}

parents_of_egg <- function(egg, relationships_by_id) {
  relationship <- relationships_by_id[[egg$relationship_id %||% ""]]
  if (is.null(relationship)) {
    return(character(0L))
  }
  members <- relationship$members %||% list()
  unlist(members, use.names = FALSE)
}

build_partner_map <- function(pedigree) {
  partners <- list()
  for (relationship in pedigree$relationships %||% list()) {
    members <- unlist(relationship$members %||% list(), use.names = FALSE)
    for (individual_id in members) {
      others <- setdiff(members, individual_id)
      partners[[individual_id]] <- c(partners[[individual_id]] %||% character(0L), others)
    }
  }
  partners
}

assign_generations <- function(individual_ids, parents_of) {
  generations <- stats::setNames(rep(list(NULL), length(individual_ids)), individual_ids)
  queue <- character(0L)
  for (individual_id in individual_ids) {
    if (length(parents_of[[individual_id]] %||% character(0L)) == 0L) {
      generations[[individual_id]] <- 0L
      queue <- c(queue, individual_id)
    }
  }

  while (length(queue) > 0L) {
    current <- queue[[1L]]
    queue <- queue[-1L]
    current_generation <- generations[[current]]
    if (is.null(current_generation)) next
    for (individual_id in individual_ids) {
      parents <- parents_of[[individual_id]] %||% character(0L)
      if (!(current %in% parents)) next
      parent_generations <- Filter(
        Negate(is.null),
        lapply(parents, function(parent) generations[[parent]])
      )
      if (length(parent_generations) != length(parents)) next
      candidate <- max(unlist(parent_generations)) + 1L
      existing <- generations[[individual_id]]
      if (is.null(existing) || candidate > existing) {
        generations[[individual_id]] <- candidate
        queue <- c(queue, individual_id)
      }
    }
  }

  generations
}

align_partners <- function(generations, partners_of) {
  changed <- TRUE
  while (changed) {
    changed <- FALSE
    for (individual_id in names(generations)) {
      current <- generations[[individual_id]]
      partner_generations <- Filter(
        Negate(is.null),
        lapply(partners_of[[individual_id]] %||% character(0L),
               function(partner) generations[[partner]])
      )
      if (length(partner_generations) == 0L) next
      target <- max(unlist(partner_generations))
      if (is.null(current) || target > current) {
        generations[[individual_id]] <- target
        changed <- TRUE
      }
    }
  }
  generations
}

label_for <- function(generation) {
  if (is.null(generation)) {
    return(UNKNOWN_GENERATION_LABEL)
  }
  to_roman(generation + 1L)
}

to_roman <- function(number) {
  if (number <= 0L) {
    return(UNKNOWN_GENERATION_LABEL)
  }
  numerals <- list(
    c(1000L, "M"), c(900L, "CM"), c(500L, "D"), c(400L, "CD"),
    c(100L, "C"), c(90L, "XC"), c(50L, "L"), c(40L, "XL"),
    c(10L, "X"), c(9L, "IX"), c(5L, "V"), c(4L, "IV"),
    c(1L, "I")
  )
  remainder <- number
  result <- character(0L)
  for (entry in numerals) {
    value <- as.integer(entry[[1L]])
    symbol <- entry[[2L]]
    while (remainder >= value) {
      result <- c(result, symbol)
      remainder <- remainder - value
    }
  }
  paste(result, collapse = "")
}

`%||%` <- function(a, b) if (is.null(a)) b else a
