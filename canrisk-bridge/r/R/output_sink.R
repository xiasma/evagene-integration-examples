# Write the CanRisk payload to disk and optionally open canrisk.org.

CANRISK_UPLOAD_URL <- "https://canrisk.org"

#' Build the default filename for a pedigree export.
#'
#' @param pedigree_id A UUID string.
filename_for <- function(pedigree_id) {
  sprintf("evagene-canrisk-%s.txt", substr(pedigree_id, 1L, 8L))
}

#' Save the payload to disk under the output directory.
#'
#' @param output_dir Directory to write into; created if missing.
#' @param pedigree_id UUID string, used to derive the filename.
#' @param payload Character scalar containing the ##CanRisk 2.0 body.
#' @return The absolute path of the saved file.
save_canrisk <- function(output_dir, pedigree_id, payload) {
  dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)
  path <- file.path(output_dir, filename_for(pedigree_id))
  # writeBin preserves the exact bytes -- writeLines would rewrite
  # line endings to the platform default, corrupting the payload.
  connection <- file(path, open = "wb")
  on.exit(close(connection), add = TRUE)
  writeBin(charToRaw(payload), connection)
  normalizePath(path, winslash = "\\", mustWork = TRUE)
}

#' Open the canrisk.org upload page via the supplied browser function.
#'
#' The browser is injected so tests never shell out.  The production
#' entry point passes `utils::browseURL`.
#'
#' @param browser A function accepting a single URL string.
open_upload_page <- function(browser) {
  browser(CANRISK_UPLOAD_URL)
  invisible(NULL)
}
