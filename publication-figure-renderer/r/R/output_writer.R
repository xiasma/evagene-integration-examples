# Writes an SVG document to a file on disk.  Isolating this makes the
# rest of the pipeline testable without touching the filesystem.

#' Write an SVG document to disk as UTF-8.
#'
#' @param svg_text The SVG document as a single character string.
#' @param path File path to write.
#' @return `path` (invisibly), for chaining.
write_svg <- function(svg_text, path) {
  writeBin(charToRaw(enc2utf8(svg_text)), path)
  invisible(path)
}
