# Declares the three BayesMendel models this demo compares.
#
# Keeping the registry in one place means adding a fourth model is a
# one-line edit -- no presenter, no builder, no client needs to change.

#' The BayesMendel models compared by this demo, in display order.
#' @return Character vector of model names.
bayesmendel_models <- function() {
  c("BRCAPRO", "MMRpro", "PancPRO")
}
