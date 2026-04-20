test_that("writes the SVG text to the requested path as UTF-8", {
  svg_text <- "<svg xmlns=\"http://www.w3.org/2000/svg\"><text>Caf\u00e9</text></svg>"
  path <- tempfile(fileext = ".svg")
  on.exit(unlink(path), add = TRUE)

  returned <- write_svg(svg_text, path)

  expect_equal(returned, path)
  expect_true(file.exists(path))
  round_tripped <- readChar(path, file.info(path)$size, useBytes = TRUE)
  Encoding(round_tripped) <- "UTF-8"
  expect_equal(round_tripped, svg_text)
})
