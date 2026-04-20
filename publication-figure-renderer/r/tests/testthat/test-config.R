VALID_UUID <- "11111111-1111-1111-1111-111111111111"

test_that("accepts a minimal argv with --output and defaults sensibly", {
  config <- load_config(
    c(VALID_UUID, "--output", "fig.svg"),
    list(EVAGENE_API_KEY = "evg_test")
  )

  expect_equal(config$base_url, "https://evagene.net")
  expect_equal(config$api_key, "evg_test")
  expect_equal(config$pedigree_id, VALID_UUID)
  expect_equal(config$output_path, "fig.svg")
  expect_false(config$deidentify)
  expect_equal(config$label_style, "generation-number")
  expect_null(config$width)
  expect_null(config$height)
})

test_that("honours a custom base URL", {
  config <- load_config(
    c(VALID_UUID, "--output", "fig.svg"),
    list(EVAGENE_API_KEY = "evg_test", EVAGENE_BASE_URL = "https://evagene.example")
  )
  expect_equal(config$base_url, "https://evagene.example")
})

test_that("parses --deidentify and --label-style", {
  config <- load_config(
    c(VALID_UUID, "--output", "fig.svg", "--deidentify", "--label-style", "initials"),
    list(EVAGENE_API_KEY = "evg_test")
  )
  expect_true(config$deidentify)
  expect_equal(config$label_style, "initials")
})

test_that("parses --width and --height as positive integers", {
  config <- load_config(
    c(VALID_UUID, "--output", "fig.svg", "--width", "800", "--height", "600"),
    list(EVAGENE_API_KEY = "evg_test")
  )
  expect_equal(config$width, 800L)
  expect_equal(config$height, 600L)
})

test_that("missing API key raises config_error", {
  expect_error(
    load_config(c(VALID_UUID, "--output", "fig.svg"), list()),
    class = "config_error"
  )
})

test_that("missing --output raises config_error", {
  expect_error(
    load_config(c(VALID_UUID), list(EVAGENE_API_KEY = "evg_test")),
    class = "config_error"
  )
})

test_that("pedigree id must be a UUID", {
  expect_error(
    load_config(
      c("not-a-uuid", "--output", "fig.svg"),
      list(EVAGENE_API_KEY = "evg_test")
    ),
    class = "config_error"
  )
})

test_that("unknown --label-style raises config_error", {
  expect_error(
    load_config(
      c(VALID_UUID, "--output", "fig.svg", "--label-style", "anagram"),
      list(EVAGENE_API_KEY = "evg_test")
    ),
    class = "config_error"
  )
})

test_that("non-integer --width raises config_error", {
  expect_error(
    load_config(
      c(VALID_UUID, "--output", "fig.svg", "--width", "tall"),
      list(EVAGENE_API_KEY = "evg_test")
    ),
    class = "config_error"
  )
})
