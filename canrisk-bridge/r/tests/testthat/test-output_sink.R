PEDIGREE_ID <- "a1cfe665-2e95-4386-9eb8-53d46095478a"

spy_browser <- function() {
  opened <- character(0)
  browser <- function(url) {
    opened <<- c(opened, url)
  }
  list(browser = browser, opened = function() opened)
}

test_that("filename uses the first eight chars of the UUID", {
  expect_equal(filename_for(PEDIGREE_ID), "evagene-canrisk-a1cfe665.txt")
})

test_that("save writes the payload to the named file in the output dir", {
  temp_dir <- tempfile("canrisk-bridge-")
  dir.create(temp_dir)
  on.exit(unlink(temp_dir, recursive = TRUE), add = TRUE)

  payload <- paste0(CANRISK_HEADER, "\nFamID\tName\n")
  saved <- save_canrisk(temp_dir, PEDIGREE_ID, payload)

  expect_equal(basename(saved), "evagene-canrisk-a1cfe665.txt")
  expect_equal(readChar(saved, file.info(saved)$size, useBytes = TRUE), payload)
})

test_that("save creates the output dir if it does not exist", {
  temp_dir <- tempfile("canrisk-bridge-")
  on.exit(unlink(temp_dir, recursive = TRUE), add = TRUE)
  nested <- file.path(temp_dir, "nested", "dir")

  save_canrisk(nested, PEDIGREE_ID, paste0(CANRISK_HEADER, "\n"))

  expect_true(dir.exists(nested))
})

test_that("open_upload_page delegates to the injected browser", {
  spy <- spy_browser()

  open_upload_page(spy$browser)

  expect_equal(spy$opened(), "https://canrisk.org")
})
