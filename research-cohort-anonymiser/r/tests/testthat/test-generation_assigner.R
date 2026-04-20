basic_pedigree <- function() {
  list(
    individuals = list(
      list(id = "gf"),
      list(id = "gm"),
      list(id = "parent"),
      list(id = "spouse"),
      list(id = "child")
    ),
    relationships = list(
      list(id = "r-gp", members = list("gf", "gm")),
      list(id = "r-parents", members = list("parent", "spouse"))
    ),
    eggs = list(
      list(id = "e1", individual_id = "parent", relationship_id = "r-gp"),
      list(id = "e2", individual_id = "child", relationship_id = "r-parents")
    )
  )
}

test_that("founders are generation I", {
  labels <- assign_generation_labels(basic_pedigree())
  expect_equal(labels[["gf"]], "I")
  expect_equal(labels[["gm"]], "I")
})

test_that("children and grandchildren get successive roman numerals", {
  labels <- assign_generation_labels(basic_pedigree())
  expect_equal(labels[["parent"]], "II")
  expect_equal(labels[["child"]], "III")
})

test_that("spouse with no parents is aligned to partner generation", {
  labels <- assign_generation_labels(basic_pedigree())
  expect_equal(labels[["spouse"]], "II")
})

test_that("consanguineous family yields stable labels", {
  pedigree <- list(
    individuals = list(
      list(id = "gf1"), list(id = "gm1"),
      list(id = "gf2"), list(id = "gm2"),
      list(id = "parentA"), list(id = "parentB"),
      list(id = "child")
    ),
    relationships = list(
      list(id = "gp1", members = list("gf1", "gm1")),
      list(id = "gp2", members = list("gf2", "gm2")),
      list(id = "pr", members = list("parentA", "parentB"), consanguinity = 0.0625)
    ),
    eggs = list(
      list(id = "e1", individual_id = "parentA", relationship_id = "gp1"),
      list(id = "e2", individual_id = "parentB", relationship_id = "gp2"),
      list(id = "e3", individual_id = "child", relationship_id = "pr")
    )
  )
  labels <- assign_generation_labels(pedigree)
  expect_equal(labels[["parentA"]], "II")
  expect_equal(labels[["parentB"]], "II")
  expect_equal(labels[["child"]], "III")
})

test_that("individual with unresolvable parent falls back to unknown label", {
  pedigree <- list(
    individuals = list(list(id = "ghost_child")),
    relationships = list(list(id = "r-ghost", members = list("phantom"))),
    eggs = list(list(id = "e", individual_id = "ghost_child",
                     relationship_id = "r-ghost"))
  )
  labels <- assign_generation_labels(pedigree)
  expect_equal(labels[["ghost_child"]], "G?")
})
