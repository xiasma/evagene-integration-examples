test_that("generation-number style labels the eldest generation with 'I-n'", {
  detail <- read_fixture_json("sample-detail.json")

  mapping <- build_label_mapping(detail, "generation-number")

  expect_equal(mapping[["11111111-1111-1111-1111-111111111111"]], "I-1")
  expect_equal(mapping[["22222222-2222-2222-2222-222222222222"]], "I-2")
  expect_equal(mapping[["33333333-3333-3333-3333-333333333333"]], "II-1")
  expect_equal(mapping[["44444444-4444-4444-4444-444444444444"]], "II-2")
  expect_equal(mapping[["55555555-5555-5555-5555-555555555555"]], "III-1")
})

test_that("initials style takes the first letter of each word", {
  detail <- read_fixture_json("sample-detail.json")

  mapping <- build_label_mapping(detail, "initials")

  expect_equal(mapping[["11111111-1111-1111-1111-111111111111"]], "RS")
  expect_equal(mapping[["55555555-5555-5555-5555-555555555555"]], "SS")
})

test_that("off style produces an empty label for every individual", {
  detail <- read_fixture_json("sample-detail.json")

  mapping <- build_label_mapping(detail, "off")

  expect_true(all(mapping == ""))
})

test_that("y-coordinate falls back for generation when generation is missing", {
  # Real pedigrees frequently have no explicit `generation` value.  Fall
  # back on the layout y-coordinate: smaller y = earlier generation.
  detail <- list(
    individuals = list(
      list(id = "11111111-1111-1111-1111-111111111111", y = 560),
      list(id = "22222222-2222-2222-2222-222222222222", y = 200),
      list(id = "33333333-3333-3333-3333-333333333333", y = 360),
      list(id = "44444444-4444-4444-4444-444444444444", y = 200)
    )
  )

  mapping <- build_label_mapping(detail, "generation-number")

  expect_equal(mapping[["22222222-2222-2222-2222-222222222222"]], "I-1")
  expect_equal(mapping[["44444444-4444-4444-4444-444444444444"]], "I-2")
  expect_equal(mapping[["33333333-3333-3333-3333-333333333333"]], "II-1")
  expect_equal(mapping[["11111111-1111-1111-1111-111111111111"]], "III-1")
})

test_that("unknown generation and missing y fall back to '?-n'", {
  detail <- list(
    individuals = list(
      list(id = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa", display_name = "Alice"),
      list(id = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb", display_name = "Bob")
    )
  )

  mapping <- build_label_mapping(detail, "generation-number")

  expect_equal(mapping[["aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"]], "?-1")
  expect_equal(mapping[["bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"]], "?-2")
})
