# Pure transform: (SVG text + old_name -> new_label mapping) -> SVG text
# with display names replaced inside <text> elements only.
#
# xml2 parses the document into a proper node tree, so we never touch
# attribute strings, never compete with SVG's CDATA/escaping rules, and
# cannot be fooled by adversarial characters in names.

SVG_NS <- "http://www.w3.org/2000/svg"

#' Raise an invalid_svg_error condition.
#' @noRd
stop_invalid_svg <- function(message) {
  stop(structure(
    list(message = message, call = sys.call(-1)),
    class = c("invalid_svg_error", "error", "condition")
  ))
}

#' Return the input SVG text with display names replaced and optional
#' width/height overrides applied to the root `<svg>` element.
#'
#' @param svg_text Raw SVG document as a single character string.
#' @param name_to_label Named character vector: names are the original
#'   display names to replace; values are the replacement labels.
#'   An empty-string label removes the matching <text> element entirely,
#'   so a "--label-style=off" pass still leaves valid SVG.
#' @param width Optional integer; overrides the root `width` attribute.
#' @param height Optional integer; overrides the root `height` attribute.
#' @return The transformed SVG as a single character string.
deidentify_svg <- function(svg_text,
                           name_to_label = character(0),
                           width = NULL, height = NULL) {
  doc <- tryCatch(
    xml2::read_xml(svg_text),
    error = function(e) {
      stop_invalid_svg(sprintf("Could not parse SVG: %s", conditionMessage(e)))
    }
  )

  apply_dimensions(doc, width, height)
  apply_label_replacements(doc, name_to_label)

  as.character(doc)
}

apply_dimensions <- function(doc, width, height) {
  root <- xml2::xml_root(doc)
  if (!is.null(width)) {
    xml2::xml_set_attr(root, "width", as.character(width))
  }
  if (!is.null(height)) {
    xml2::xml_set_attr(root, "height", as.character(height))
  }
}

apply_label_replacements <- function(doc, name_to_label) {
  if (length(name_to_label) == 0L) {
    return(invisible(NULL))
  }
  text_nodes <- xml2::xml_find_all(
    doc, "//svg:text",
    ns = c(svg = SVG_NS)
  )
  lookup_names <- names(name_to_label)
  for (node in text_nodes) {
    current <- xml2::xml_text(node)
    if (!current %in% lookup_names) {
      next
    }
    replacement <- unname(name_to_label[[current]])
    if (!nzchar(replacement)) {
      xml2::xml_remove(node)
    } else {
      xml2::xml_text(node) <- replacement
    }
  }
  invisible(NULL)
}
