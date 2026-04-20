# Thin client for the Evagene REST endpoints this demo needs.
#
# Factory make_evagene_client(gateway, base_url, api_key) returns a
# named list of methods:
#   $get_pedigree_detail(pedigree_id)
#   $create_pedigree(display_name)
#   $create_individual(display_name, biological_sex)
#   $add_individual_to_pedigree(pedigree_id, individual_id)
#   $designate_as_proband(individual_id)
#   $add_relative(pedigree_id, relative_of, relative_type, display_name, biological_sex)
#   $delete_pedigree(pedigree_id)
#   $rebuild_pedigree(anonymised)
#
# The rebuild method mirrors the intake-form demo's sequence.

HTTP_OK_LOWER <- 200L
HTTP_OK_UPPER <- 300L

stop_api <- function(message) {
  stop(structure(
    list(message = message, call = sys.call(-1)),
    class = c("api_error", "error", "condition")
  ))
}

#' Build an Evagene client closure.
#'
#' @param gateway Gateway function (see http_gateway.R).
#' @param base_url Evagene base URL (trailing slash optional).
#' @param api_key  Value for the `X-API-Key` header.
#' @return A named list of methods.
make_evagene_client <- function(gateway, base_url, api_key) {
  base <- sub("/$", "", base_url)
  headers <- c(
    "X-API-Key" = api_key,
    "Content-Type" = "application/json",
    "Accept" = "application/json"
  )

  request <- function(method, path, body) {
    request_json <- if (is.null(body)) NULL else jsonlite::toJSON(body, auto_unbox = TRUE)
    response <- gateway(list(
      method = method,
      url = paste0(base, path),
      headers = headers,
      body_json = request_json
    ))
    if (response$status < HTTP_OK_LOWER || response$status >= HTTP_OK_UPPER) {
      stop_api(sprintf("Evagene API returned HTTP %d for %s %s",
                       response$status, method, path))
    }
    response
  }

  request_json <- function(method, path, body) {
    response <- request(method, path, body)
    parsed <- tryCatch(
      jsonlite::fromJSON(response$json_body, simplifyVector = FALSE),
      error = function(e) {
        stop_api(sprintf("Evagene API returned invalid JSON: %s", conditionMessage(e)))
      }
    )
    if (!is.list(parsed) || is.null(names(parsed))) {
      stop_api("Evagene API returned non-object JSON")
    }
    parsed
  }

  request_ignoring_body <- function(method, path, body) {
    invisible(request(method, path, body))
  }

  require_str <- function(payload, key) {
    value <- payload[[key]]
    if (!is.character(value) || length(value) != 1L || is.na(value)) {
      stop_api(sprintf("Evagene response is missing string field '%s'", key))
    }
    value
  }

  require_dict <- function(payload, key) {
    value <- payload[[key]]
    if (!is.list(value) || is.null(names(value))) {
      stop_api(sprintf("Evagene response is missing object field '%s'", key))
    }
    value
  }

  client <- list()

  client$get_pedigree_detail <- function(pedigree_id) {
    request_json("GET", sprintf("/api/pedigrees/%s", pedigree_id), NULL)
  }

  client$create_pedigree <- function(display_name) {
    payload <- request_json("POST", "/api/pedigrees", list(display_name = display_name))
    require_str(payload, "id")
  }

  client$create_individual <- function(display_name, biological_sex) {
    payload <- request_json("POST", "/api/individuals",
                            list(display_name = display_name, biological_sex = biological_sex))
    require_str(payload, "id")
  }

  client$add_individual_to_pedigree <- function(pedigree_id, individual_id) {
    request_ignoring_body(
      "POST",
      sprintf("/api/pedigrees/%s/individuals/%s", pedigree_id, individual_id),
      list()
    )
  }

  client$designate_as_proband <- function(individual_id) {
    request_ignoring_body("PATCH", sprintf("/api/individuals/%s", individual_id),
                          list(proband = 1L))
  }

  client$add_relative <- function(pedigree_id, relative_of, relative_type,
                                  display_name, biological_sex) {
    payload <- request_json(
      "POST",
      sprintf("/api/pedigrees/%s/register/add-relative", pedigree_id),
      list(
        relative_of = relative_of,
        relative_type = relative_type,
        display_name = display_name,
        biological_sex = biological_sex
      )
    )
    require_str(require_dict(payload, "individual"), "id")
  }

  client$delete_pedigree <- function(pedigree_id) {
    request_ignoring_body("DELETE", sprintf("/api/pedigrees/%s", pedigree_id), NULL)
  }

  client$rebuild_pedigree <- function(anonymised) {
    rebuild_pedigree(client, anonymised)
  }

  client
}

# ---- Rebuild orchestration -------------------------------------------------

rebuild_pedigree <- function(client, anonymised) {
  proband <- require_proband(anonymised)
  pedigree_id <- client$create_pedigree(anonymised$display_name %||% "Anon")
  proband_new_id <- client$create_individual(proband$display_name, proband$biological_sex)
  client$add_individual_to_pedigree(pedigree_id, proband_new_id)
  client$designate_as_proband(proband_new_id)

  source_to_new_id <- list()
  source_to_new_id[[proband$id]] <- proband_new_id

  relationship_maps <- build_relationship_maps(anonymised)
  individuals_by_id <- stats::setNames(
    anonymised$individuals,
    vapply(anonymised$individuals, function(individual) individual$id, character(1L))
  )

  queue <- c(proband$id)
  visited <- c(proband$id)
  while (length(queue) > 0L) {
    anchor <- queue[[1L]]
    queue <- queue[-1L]
    neighbours <- neighbours_of(anchor, relationship_maps, individuals_by_id)
    for (entry in neighbours) {
      neighbour_id <- entry$id
      if (neighbour_id %in% visited) next
      visited <- c(visited, neighbour_id)
      neighbour <- individuals_by_id[[neighbour_id]]
      new_id <- client$add_relative(
        pedigree_id,
        source_to_new_id[[anchor]],
        entry$relative_type,
        neighbour$display_name,
        neighbour$biological_sex
      )
      source_to_new_id[[neighbour_id]] <- new_id
      queue <- c(queue, neighbour_id)
    }
  }
  pedigree_id
}

require_proband <- function(anonymised) {
  for (individual in anonymised$individuals) {
    raw <- individual$proband %||% 0L
    if (!identical(as.integer(raw), 0L)) {
      return(individual)
    }
  }
  stop_api("Anonymised pedigree has no proband; --as-new-pedigree needs one.")
}

build_relationship_maps <- function(anonymised) {
  relationships_by_id <- stats::setNames(
    anonymised$relationships %||% list(),
    vapply(anonymised$relationships %||% list(), function(relationship) relationship$id,
           character(1L))
  )
  parents_of <- list()
  children_of <- list()
  for (egg in anonymised$eggs %||% list()) {
    children <- if (!is.null(egg$individual_id)) egg$individual_id else unlist(
      egg$individual_ids %||% list(), use.names = FALSE)
    relationship <- relationships_by_id[[egg$relationship_id %||% ""]]
    if (is.null(relationship)) next
    parents <- unlist(relationship$members %||% list(), use.names = FALSE)
    for (child in children) {
      parents_of[[child]] <- c(parents_of[[child]] %||% character(0L), parents)
      for (parent in parents) {
        children_of[[parent]] <- c(children_of[[parent]] %||% character(0L), child)
      }
    }
  }
  list(parents_of = parents_of, children_of = children_of)
}

neighbours_of <- function(anchor_id, relationship_maps, individuals_by_id) {
  result <- list()
  for (parent_id in relationship_maps$parents_of[[anchor_id]] %||% character(0L)) {
    parent <- individuals_by_id[[parent_id]]
    result[[length(result) + 1L]] <- list(
      id = parent_id,
      relative_type = parent_relative_type(parent$biological_sex)
    )
    for (sibling_id in relationship_maps$children_of[[parent_id]] %||% character(0L)) {
      if (identical(sibling_id, anchor_id)) next
      sibling <- individuals_by_id[[sibling_id]]
      result[[length(result) + 1L]] <- list(
        id = sibling_id,
        relative_type = sibling_relative_type(sibling$biological_sex)
      )
    }
  }
  for (child_id in relationship_maps$children_of[[anchor_id]] %||% character(0L)) {
    child <- individuals_by_id[[child_id]]
    result[[length(result) + 1L]] <- list(
      id = child_id,
      relative_type = child_relative_type(child$biological_sex)
    )
  }
  result
}

parent_relative_type <- function(sex) if (identical(sex, "female")) "mother" else "father"
sibling_relative_type <- function(sex) if (identical(sex, "female")) "sister" else "brother"
child_relative_type <- function(sex) if (identical(sex, "female")) "daughter" else "son"
