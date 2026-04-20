SVG_NS <- c(svg = "http://www.w3.org/2000/svg")

text_contents <- function(doc) {
  xml2::xml_text(xml2::xml_find_all(doc, "//svg:text", ns = SVG_NS))
}

attribute_snapshot <- function(doc, xpath) {
  nodes <- xml2::xml_find_all(doc, xpath, ns = SVG_NS)
  lapply(nodes, xml2::xml_attrs)
}

test_that("display names disappear when replaced with generation-number labels", {
  svg_text <- read_fixture_text("sample.svg")
  detail <- read_fixture_json("sample-detail.json")
  id_to_label <- build_label_mapping(detail, "generation-number")
  name_to_label <- stats::setNames(
    c(id_to_label[[detail$individuals[[1L]]$id]],
      id_to_label[[detail$individuals[[2L]]$id]],
      id_to_label[[detail$individuals[[3L]]$id]],
      id_to_label[[detail$individuals[[4L]]$id]],
      id_to_label[[detail$individuals[[5L]]$id]]),
    c("Robert Smith", "Mary Smith", "David Smith",
      "Linda <O'Brien> & Co", "Sarah Smith")
  )

  rendered <- deidentify_svg(svg_text, name_to_label)

  for (name in c("Robert Smith", "Mary Smith", "David Smith",
                 "Linda <O'Brien> & Co", "Sarah Smith")) {
    expect_false(grepl(name, rendered, fixed = TRUE))
  }

  rendered_doc <- xml2::read_xml(rendered)
  expect_equal(
    sort(text_contents(rendered_doc)),
    sort(c("I-1", "I-2", "II-1", "II-2", "III-1"))
  )
})

test_that("non-text attributes are preserved structurally", {
  svg_text <- read_fixture_text("sample.svg")
  original_doc <- xml2::read_xml(svg_text)
  detail <- read_fixture_json("sample-detail.json")
  id_to_label <- build_label_mapping(detail, "generation-number")
  name_to_label <- c(
    "Robert Smith" = unname(id_to_label[[detail$individuals[[1L]]$id]]),
    "Mary Smith" = unname(id_to_label[[detail$individuals[[2L]]$id]]),
    "David Smith" = unname(id_to_label[[detail$individuals[[3L]]$id]]),
    "Linda <O'Brien> & Co" = unname(id_to_label[[detail$individuals[[4L]]$id]]),
    "Sarah Smith" = unname(id_to_label[[detail$individuals[[5L]]$id]])
  )

  rendered_doc <- xml2::read_xml(deidentify_svg(svg_text, name_to_label))

  for (xpath in c("//svg:rect", "//svg:circle", "//svg:polygon", "//svg:line")) {
    expect_equal(
      attribute_snapshot(rendered_doc, xpath),
      attribute_snapshot(original_doc, xpath),
      info = xpath
    )
  }
})

test_that("names containing XML-special characters are handled safely", {
  svg_text <- read_fixture_text("sample.svg")
  name_to_label <- c("Linda <O'Brien> & Co" = "II-2")

  rendered <- deidentify_svg(svg_text, name_to_label)

  # Replacement succeeded.
  expect_true(grepl("II-2", rendered, fixed = TRUE))
  # The original, properly-escaped entity string is no longer present.
  expect_false(grepl("Linda", rendered, fixed = TRUE))
  # And the re-serialised document must still parse.
  expect_silent(xml2::read_xml(rendered))
})

test_that("a label containing injection-shaped characters is text-escaped on output", {
  svg_text <- read_fixture_text("sample.svg")
  name_to_label <- c("Robert Smith" = "<script>alert(1)</script>")

  rendered <- deidentify_svg(svg_text, name_to_label)

  expect_false(grepl("<script>", rendered, fixed = TRUE))
  expect_true(grepl("&lt;script&gt;", rendered, fixed = TRUE))
  # Round-trip must still parse.
  expect_silent(xml2::read_xml(rendered))
})

test_that("an empty-string label removes the <text> element rather than leaving an empty node", {
  svg_text <- read_fixture_text("sample.svg")
  name_to_label <- c("Sarah Smith" = "")

  rendered <- deidentify_svg(svg_text, name_to_label)

  rendered_doc <- xml2::read_xml(rendered)
  expect_false("Sarah Smith" %in% text_contents(rendered_doc))
  # All other labels survive.
  expect_true(all(c("Robert Smith", "Mary Smith") %in% text_contents(rendered_doc)))
})

test_that("width and height overrides update the root attributes only", {
  svg_text <- read_fixture_text("sample.svg")

  rendered <- deidentify_svg(svg_text, character(0), width = 1024L, height = 768L)

  rendered_doc <- xml2::read_xml(rendered)
  root <- xml2::xml_root(rendered_doc)
  expect_equal(xml2::xml_attr(root, "width"), "1024")
  expect_equal(xml2::xml_attr(root, "height"), "768")
  # viewBox must survive untouched -- it anchors the print-quality scaling.
  original_doc <- xml2::read_xml(svg_text)
  expect_equal(
    xml2::xml_attr(root, "viewBox"),
    xml2::xml_attr(xml2::xml_root(original_doc), "viewBox")
  )
})

test_that("matches the canonical deidentified fixture structurally", {
  svg_text <- read_fixture_text("sample.svg")
  expected_doc <- xml2::read_xml(read_fixture_text("deidentified.svg"))
  detail <- read_fixture_json("sample-detail.json")
  id_to_label <- build_label_mapping(detail, "generation-number")
  name_to_label <- c(
    "Robert Smith" = unname(id_to_label[[detail$individuals[[1L]]$id]]),
    "Mary Smith" = unname(id_to_label[[detail$individuals[[2L]]$id]]),
    "David Smith" = unname(id_to_label[[detail$individuals[[3L]]$id]]),
    "Linda <O'Brien> & Co" = unname(id_to_label[[detail$individuals[[4L]]$id]]),
    "Sarah Smith" = unname(id_to_label[[detail$individuals[[5L]]$id]])
  )

  rendered_doc <- xml2::read_xml(deidentify_svg(svg_text, name_to_label))

  expect_equal(
    sort(text_contents(rendered_doc)),
    sort(text_contents(expected_doc))
  )
  expect_equal(
    length(xml2::xml_find_all(rendered_doc, "//svg:*", ns = SVG_NS)),
    length(xml2::xml_find_all(expected_doc, "//svg:*", ns = SVG_NS))
  )
})

test_that("a malformed SVG raises invalid_svg_error", {
  expect_error(
    deidentify_svg("<svg><text>broken", character(0)),
    class = "invalid_svg_error"
  )
})
