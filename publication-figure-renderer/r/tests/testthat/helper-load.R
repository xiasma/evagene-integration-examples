# Sourced by testthat before any test file.  Loads the project's R/ files
# so the tests can exercise them without installing the package.

r_dir <- normalizePath(file.path("..", "..", "R"), mustWork = TRUE)
for (source_file in list.files(r_dir, pattern = "\\.R$", full.names = TRUE)) {
  source(source_file, local = FALSE)
}

FIXTURES <- normalizePath(file.path("..", "..", "..", "fixtures"), mustWork = TRUE)

read_fixture_text <- function(name) {
  path <- file.path(FIXTURES, name)
  readChar(path, file.info(path)$size, useBytes = TRUE)
}

read_fixture_json <- function(name) {
  jsonlite::fromJSON(file.path(FIXTURES, name), simplifyVector = FALSE)
}
