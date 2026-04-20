# Sourced by testthat before any test file.  Loads the project's R/ files
# so the tests can exercise them without installing the package.

r_dir <- normalizePath(file.path("..", "..", "R"), mustWork = TRUE)
for (source_file in list.files(r_dir, pattern = "\\.R$", full.names = TRUE)) {
  source(source_file, local = FALSE)
}

fixture_path <- function(name) {
  normalizePath(
    file.path("..", "..", "..", "fixtures", paste0(name, ".json")),
    mustWork = TRUE
  )
}

load_fixture <- function(name) {
  jsonlite::fromJSON(fixture_path(name), simplifyVector = FALSE)
}
