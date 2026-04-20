# Thin Evagene REST client tailored for the Quarto notebook narrative.
#
# Same five operations as the Python twin, packaged as a named list of
# closures so the Quarto cells stay tight.  The gateway is injected so
# tests can fake it without touching the network.

HTTP_OK_LOWER <- 200L
HTTP_OK_UPPER <- 300L
SCRATCH_PREFIX <- "[scratch] notebook-explorer"

#' Raise an api_error condition.
#' @noRd
stop_api <- function(message) {
  stop(structure(
    list(message = message, call = sys.call(-1)),
    class = c("api_error", "error", "condition")
  ))
}

#' Construct an Evagene client bound to a gateway and credentials.
#'
#' @param gateway A function built by `make_httr2_gateway()`.
#' @param base_url Evagene base URL (trailing slash optional).
#' @param api_key Value for the `X-API-Key` header.
#' @return A list of closures: `get_pedigrees`, `run_risk`,
#'   `clone_pedigree_for_exploration`, `delete_pedigree`,
#'   `add_relative`, `add_disease_to_individual`,
#'   `add_disease_to_pedigree`, `patch_individual`,
#'   `get_register`, `evagene_url`.
evagene_client <- function(gateway, base_url, api_key) {
  base <- sub("/$", "", base_url)
  headers <- c(
    "X-API-Key" = api_key,
    "Content-Type" = "application/json",
    "Accept" = "application/json"
  )

  do_request <- function(method, path, body = NULL) {
    url <- paste0(base, path)
    request <- list(method = method, url = url, headers = headers)
    if (!is.null(body)) {
      request$body_json <- jsonlite::toJSON(body, auto_unbox = TRUE, null = "null")
    }
    response <- gateway(request)
    if (response$status < HTTP_OK_LOWER || response$status >= HTTP_OK_UPPER) {
      stop_api(sprintf(
        "Evagene API returned HTTP %d for %s %s",
        response$status, method, path
      ))
    }
    response
  }

  parse_json <- function(response) {
    tryCatch(
      jsonlite::fromJSON(response$body_string, simplifyVector = FALSE),
      error = function(e) stop_api(sprintf(
        "Evagene API returned invalid JSON: %s", conditionMessage(e)
      ))
    )
  }

  require_object <- function(parsed, where) {
    if (!is.list(parsed) || is.null(names(parsed))) {
      stop_api(sprintf("Evagene API returned non-object JSON from %s", where))
    }
    parsed
  }

  list(
    get_pedigrees = function() {
      parsed <- parse_json(do_request("GET", "/api/pedigrees"))
      if (!is.list(parsed) || (length(parsed) > 0L && !is.null(names(parsed)))) {
        stop_api("Expected a JSON array from GET /api/pedigrees.")
      }
      parsed
    },
    run_risk = function(pedigree_id, model, extra = list()) {
      body <- c(list(model = model), extra)
      response <- do_request(
        "POST",
        sprintf("/api/pedigrees/%s/risk/calculate", pedigree_id),
        body = body
      )
      require_object(parse_json(response), "risk/calculate")
    },
    clone_pedigree_for_exploration = function(source_pedigree_id, scratch_suffix) {
      gedcom_text <- do_request(
        "GET",
        sprintf("/api/pedigrees/%s/export.ged", source_pedigree_id)
      )$body_string
      created <- parse_json(do_request(
        "POST", "/api/pedigrees",
        body = list(display_name = sprintf("%s %s", SCRATCH_PREFIX, scratch_suffix))
      ))
      target_id <- created$id
      if (!is.character(target_id) || length(target_id) != 1L) {
        stop_api("POST /api/pedigrees did not return an 'id' string.")
      }
      do_request(
        "POST",
        sprintf("/api/pedigrees/%s/import/gedcom", target_id),
        body = list(content = gedcom_text)
      )
      target_id
    },
    delete_pedigree = function(pedigree_id) {
      do_request("DELETE", sprintf("/api/pedigrees/%s", pedigree_id))
      invisible(NULL)
    },
    add_relative = function(pedigree_id, relative_of, relative_type,
                            display_name, biological_sex = NULL) {
      body <- list(
        relative_of = relative_of,
        relative_type = relative_type,
        display_name = display_name
      )
      if (!is.null(biological_sex)) body$biological_sex <- biological_sex
      require_object(
        parse_json(do_request(
          "POST",
          sprintf("/api/pedigrees/%s/register/add-relative", pedigree_id),
          body = body
        )),
        "add-relative"
      )
    },
    add_disease_to_individual = function(individual_id, disease_id,
                                          affection_status = "affected",
                                          age_at_diagnosis = NULL) {
      body <- list(disease_id = disease_id, affection_status = affection_status)
      if (!is.null(age_at_diagnosis)) body$age_at_diagnosis <- age_at_diagnosis
      do_request(
        "POST",
        sprintf("/api/individuals/%s/diseases", individual_id),
        body = body
      )
      invisible(NULL)
    },
    add_disease_to_pedigree = function(pedigree_id, disease_id) {
      do_request(
        "POST",
        sprintf("/api/pedigrees/%s/diseases/%s", pedigree_id, disease_id),
        body = list()
      )
      invisible(NULL)
    },
    patch_individual = function(individual_id, fields) {
      do_request(
        "PATCH",
        sprintf("/api/individuals/%s", individual_id),
        body = fields
      )
      invisible(NULL)
    },
    get_register = function(pedigree_id) {
      require_object(
        parse_json(do_request(
          "GET",
          sprintf("/api/pedigrees/%s/register", pedigree_id)
        )),
        "register"
      )
    },
    evagene_url = function(pedigree_id) {
      sprintf("%s/pedigrees/%s", base, pedigree_id)
    }
  )
}
