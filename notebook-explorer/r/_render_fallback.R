# Optional renderer for environments without Quarto installed.
#
# ``quarto render explorer.qmd`` is the canonical command; this script
# produces a reasonable HTML approximation via rmarkdown + knitr by
# stripping Quarto-specific YAML and piping through Pandoc, so the
# committed ``explorer.html`` can be regenerated even on hosts without
# a Quarto installation.  Everything produced here is valid output of
# ``quarto render`` too.
#
#   Rscript _render_fallback.R
#
# The resulting ``explorer.html`` contains all executed chunks and plots.

input <- "explorer.qmd"
# Place the intermediate Rmd alongside explorer.qmd so relative paths
# (the ``R/`` folder, ``.env`` discovery) resolve identically.
rmd_path <- file.path(getwd(), "_explorer_rendered.Rmd")

lines <- readLines(input, warn = FALSE)

# Build a minimal Rmd YAML header.  Quarto-specific YAML keys (``execute:``,
# ``format:`` with html+embed-resources) are dropped; rmarkdown understands
# ``output: html_document`` alone.
header <- c(
  "---",
  "title: \"Evagene risk explorer (R / Quarto)\"",
  "author: \"Evagene integration examples\"",
  "output:",
  "  html_document:",
  "    toc: true",
  "    toc_depth: 2",
  "    self_contained: true",
  "---"
)

# Drop the existing Quarto YAML block (between two lines of ``---``).
yaml_end <- which(lines == "---")[2L]
body <- if (!is.na(yaml_end)) lines[(yaml_end + 1L):length(lines)] else lines

writeLines(c(header, body), rmd_path)

tryCatch(
  rmarkdown::render(
    rmd_path,
    output_file = file.path(getwd(), "explorer.html"),
    knit_root_dir = getwd(),
    quiet = TRUE
  ),
  finally = unlink(rmd_path)
)
cat("Wrote explorer.html\n")
