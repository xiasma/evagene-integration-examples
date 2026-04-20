# Validate a 23andMe raw genotype file and infer biological sex from it.
#
# The file is sent verbatim to Evagene's /import/23andme-raw endpoint;
# this module does *not* reinterpret genotypes or carrier state.  Its
# only jobs are to check the TSV is well-formed and to derive a
# biological_sex value we can record on the individual before import.

SEX_MALE <- "male"
SEX_FEMALE <- "female"
SEX_UNKNOWN <- "unknown"

EXPECTED_FIELDS <- 4L
Y_CHROMOSOME <- "Y"
NO_CALL <- "--"

#' Raise a genome_file_error condition.
#' @noRd
stop_genome_file <- function(message) {
  stop(structure(
    list(message = message, call = sys.call(-1)),
    class = c("genome_file_error", "error", "condition")
  ))
}

#' Read, validate, and summarise a 23andMe raw genotype TSV.
#'
#' @param path Path to a 23andMe raw genotype file.
#' @return A named list with fields `path`, `content`, `biological_sex`.
load_genome_file <- function(path) {
  if (!file.exists(path)) {
    stop_genome_file(sprintf("23andMe file not found: %s", path))
  }
  content <- tryCatch(
    paste(readLines(path, warn = FALSE), collapse = "\n"),
    error = function(e) {
      stop_genome_file(sprintf("Cannot read 23andMe file %s: %s", path, conditionMessage(e)))
    }
  )

  rows <- parse_genotype_rows(content)
  if (length(rows$chromosome) == 0L) {
    stop_genome_file(sprintf(
      paste0("%s: no genotype rows found. ",
             "Expected a TSV with columns rsid, chromosome, position, genotype."),
      path
    ))
  }

  list(
    path = path,
    content = content,
    biological_sex = infer_sex(rows$chromosome, rows$genotype)
  )
}

parse_genotype_rows <- function(content) {
  chromosomes <- character(0)
  genotypes <- character(0)
  for (raw_line in strsplit(content, "\n", fixed = TRUE)[[1L]]) {
    line <- trimws(raw_line)
    if (!nzchar(line) || startsWith(line, "#")) next
    parts <- strsplit(line, "\t", fixed = TRUE)[[1L]]
    if (length(parts) < EXPECTED_FIELDS) next
    chromosomes <- c(chromosomes, parts[[2L]])
    genotypes <- c(genotypes, trimws(parts[[4L]]))
  }
  list(chromosome = chromosomes, genotype = genotypes)
}

#' Male if any Y-chromosome SNP has a real call; female if all are no-calls.
#'
#' 23andMe reports Y-chromosome SNPs as "--" for biological females (no
#' Y chromosome present).  When a file has no Y-chromosome rows at all
#' we cannot tell, and return "unknown".
infer_sex <- function(chromosomes, genotypes) {
  y_mask <- chromosomes == Y_CHROMOSOME
  if (!any(y_mask)) {
    return(SEX_UNKNOWN)
  }
  if (any(genotypes[y_mask] != NO_CALL)) {
    return(SEX_MALE)
  }
  SEX_FEMALE
}
