test_that("partner-a fixture parses as male", {
  genome <- load_genome_file(fixture_path("partner-a-23andme.txt"))

  expect_equal(genome$biological_sex, SEX_MALE)
  expect_true(grepl("rs334", genome$content, fixed = TRUE))
})

test_that("partner-b fixture parses as female", {
  genome <- load_genome_file(fixture_path("partner-b-23andme.txt"))

  expect_equal(genome$biological_sex, SEX_FEMALE)
})

test_that("a file without Y-chromosome rows is reported as unknown", {
  scratch <- tempfile(fileext = ".txt")
  writeLines("# synthetic\nrs334\t11\t5248232\tAT", scratch)
  on.exit(unlink(scratch), add = TRUE)

  genome <- load_genome_file(scratch)
  expect_equal(genome$biological_sex, SEX_UNKNOWN)
})

test_that("a missing file raises genome_file_error", {
  expect_error(
    load_genome_file(tempfile()),
    class = "genome_file_error"
  )
})

test_that("a comments-only file raises genome_file_error", {
  scratch <- tempfile(fileext = ".txt")
  writeLines("# only comments", scratch)
  on.exit(unlink(scratch), add = TRUE)

  expect_error(load_genome_file(scratch), class = "genome_file_error")
})
