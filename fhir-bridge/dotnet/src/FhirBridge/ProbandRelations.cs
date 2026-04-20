namespace FhirBridge;

/// <summary>
/// Walks a PedigreeDetail and labels every other individual with their
/// relation to the proband.
///
/// Evagene models a family as individuals + couple relationships + eggs
/// (child belongs to a couple). From the proband's eggs we find
/// parents; from parents' eggs we find grandparents; siblings share
/// parents; children come through eggs where the proband is on the
/// couple; aunts, uncles, nieces, nephews, and first cousins follow the
/// same pattern one step further out.
/// </summary>
public sealed record RelationView(PedigreeIndividual Individual, RelativeType RelativeType);

public sealed record ProbandRelationsResult(
    PedigreeIndividual Proband,
    IReadOnlyList<RelationView> Relatives,
    IReadOnlyList<PedigreeIndividual> Unlabelled);

public static class ProbandRelations
{
    public static ProbandRelationsResult? FromProband(PedigreeDetail detail)
    {
        var proband = detail.Individuals.FirstOrDefault(i => i.Proband);
        if (proband is null)
        {
            return null;
        }
        var graph = Graph.Build(detail);
        var labels = new Dictionary<string, RelativeType>(StringComparer.Ordinal);

        LabelParents(proband.Id, graph, labels);
        LabelMaternalGrandparents(proband.Id, graph, labels);
        LabelPaternalGrandparents(proband.Id, graph, labels);
        LabelSiblings(proband.Id, graph, labels);
        LabelChildren(proband.Id, graph, labels);
        LabelAuntsAndUncles(proband.Id, graph, labels);
        LabelNiecesAndNephews(graph, labels);
        LabelFirstCousins(graph, labels);

        var relatives = new List<RelationView>();
        var unlabelled = new List<PedigreeIndividual>();
        foreach (var individual in detail.Individuals)
        {
            if (individual.Id == proband.Id)
            {
                continue;
            }
            if (labels.TryGetValue(individual.Id, out var label))
            {
                relatives.Add(new RelationView(individual, label));
            }
            else
            {
                unlabelled.Add(individual);
            }
        }
        return new ProbandRelationsResult(proband, relatives, unlabelled);
    }

    private sealed class Graph
    {
        public required Dictionary<string, PedigreeIndividual> IndividualsById { get; init; }
        public required Dictionary<string, List<string>> CouplesByPartner { get; init; }
        public required Dictionary<string, List<string>> PartnersByCouple { get; init; }
        public required Dictionary<string, List<string>> ChildrenByCouple { get; init; }
        public required Dictionary<string, string> ParentCoupleOfChild { get; init; }

        public static Graph Build(PedigreeDetail detail)
        {
            var individualsById = detail.Individuals.ToDictionary(i => i.Id, StringComparer.Ordinal);
            var couplesByPartner = new Dictionary<string, List<string>>(StringComparer.Ordinal);
            var partnersByCouple = new Dictionary<string, List<string>>(StringComparer.Ordinal);
            foreach (var relationship in detail.Relationships)
            {
                partnersByCouple[relationship.Id] = relationship.Members.ToList();
                foreach (var partner in relationship.Members)
                {
                    if (!couplesByPartner.TryGetValue(partner, out var list))
                    {
                        list = new List<string>();
                        couplesByPartner[partner] = list;
                    }
                    list.Add(relationship.Id);
                }
            }
            var childrenByCouple = new Dictionary<string, List<string>>(StringComparer.Ordinal);
            var parentCoupleOfChild = new Dictionary<string, string>(StringComparer.Ordinal);
            foreach (var egg in detail.Eggs)
            {
                if (!childrenByCouple.TryGetValue(egg.RelationshipId, out var siblings))
                {
                    siblings = new List<string>();
                    childrenByCouple[egg.RelationshipId] = siblings;
                }
                siblings.Add(egg.IndividualId);
                parentCoupleOfChild[egg.IndividualId] = egg.RelationshipId;
            }
            return new Graph
            {
                IndividualsById = individualsById,
                CouplesByPartner = couplesByPartner,
                PartnersByCouple = partnersByCouple,
                ChildrenByCouple = childrenByCouple,
                ParentCoupleOfChild = parentCoupleOfChild,
            };
        }
    }

    private sealed record Parents(string? Mother, string? Father);

    private static Parents ParentsOf(string individualId, Graph graph)
    {
        if (!graph.ParentCoupleOfChild.TryGetValue(individualId, out var coupleId))
        {
            return new Parents(null, null);
        }
        if (!graph.PartnersByCouple.TryGetValue(coupleId, out var partners))
        {
            return new Parents(null, null);
        }
        string? mother = null;
        string? father = null;
        foreach (var partnerId in partners)
        {
            if (!graph.IndividualsById.TryGetValue(partnerId, out var partner))
            {
                continue;
            }
            if (partner.BiologicalSex == BiologicalSex.Female && mother is null)
            {
                mother = partnerId;
            }
            else if (partner.BiologicalSex == BiologicalSex.Male && father is null)
            {
                father = partnerId;
            }
        }
        return new Parents(mother, father);
    }

    private static void LabelParents(string probandId, Graph graph, Dictionary<string, RelativeType> labels)
    {
        var parents = ParentsOf(probandId, graph);
        if (parents.Mother is not null)
        {
            labels[parents.Mother] = RelativeType.Mother;
        }
        if (parents.Father is not null)
        {
            labels[parents.Father] = RelativeType.Father;
        }
    }

    private static void LabelMaternalGrandparents(string probandId, Graph graph, Dictionary<string, RelativeType> labels)
    {
        var parents = ParentsOf(probandId, graph);
        if (parents.Mother is null) return;
        var grand = ParentsOf(parents.Mother, graph);
        if (grand.Mother is not null) labels[grand.Mother] = RelativeType.MaternalGrandmother;
        if (grand.Father is not null) labels[grand.Father] = RelativeType.MaternalGrandfather;
    }

    private static void LabelPaternalGrandparents(string probandId, Graph graph, Dictionary<string, RelativeType> labels)
    {
        var parents = ParentsOf(probandId, graph);
        if (parents.Father is null) return;
        var grand = ParentsOf(parents.Father, graph);
        if (grand.Mother is not null) labels[grand.Mother] = RelativeType.PaternalGrandmother;
        if (grand.Father is not null) labels[grand.Father] = RelativeType.PaternalGrandfather;
    }

    private static void LabelSiblings(string probandId, Graph graph, Dictionary<string, RelativeType> labels)
    {
        var parents = ParentsOf(probandId, graph);
        if (!graph.ParentCoupleOfChild.TryGetValue(probandId, out var coupleId))
        {
            return;
        }
        if (graph.ChildrenByCouple.TryGetValue(coupleId, out var fullSiblings))
        {
            foreach (var siblingId in fullSiblings)
            {
                if (siblingId == probandId || labels.ContainsKey(siblingId)) continue;
                if (!graph.IndividualsById.TryGetValue(siblingId, out var sibling)) continue;
                labels[siblingId] = sibling.BiologicalSex == BiologicalSex.Male
                    ? RelativeType.Brother : RelativeType.Sister;
            }
        }

        foreach (var parent in new[] { parents.Mother, parents.Father })
        {
            if (parent is null) continue;
            if (!graph.CouplesByPartner.TryGetValue(parent, out var parentCouples)) continue;
            foreach (var otherCoupleId in parentCouples)
            {
                if (otherCoupleId == coupleId) continue;
                if (!graph.ChildrenByCouple.TryGetValue(otherCoupleId, out var halves)) continue;
                foreach (var halfId in halves)
                {
                    if (halfId == probandId || labels.ContainsKey(halfId)) continue;
                    if (!graph.IndividualsById.TryGetValue(halfId, out var half)) continue;
                    labels[halfId] = half.BiologicalSex == BiologicalSex.Male
                        ? RelativeType.HalfBrother : RelativeType.HalfSister;
                }
            }
        }
    }

    private static void LabelChildren(string probandId, Graph graph, Dictionary<string, RelativeType> labels)
    {
        if (!graph.CouplesByPartner.TryGetValue(probandId, out var couples)) return;
        foreach (var coupleId in couples)
        {
            if (!graph.ChildrenByCouple.TryGetValue(coupleId, out var children)) continue;
            foreach (var childId in children)
            {
                if (labels.ContainsKey(childId)) continue;
                if (!graph.IndividualsById.TryGetValue(childId, out var child)) continue;
                labels[childId] = child.BiologicalSex == BiologicalSex.Male
                    ? RelativeType.Son : RelativeType.Daughter;
            }
        }
    }

    private static void LabelAuntsAndUncles(string probandId, Graph graph, Dictionary<string, RelativeType> labels)
    {
        var parents = ParentsOf(probandId, graph);
        if (parents.Mother is not null)
        {
            LabelSideAuntsUncles(parents.Mother, graph, labels, RelativeType.MaternalAunt, RelativeType.MaternalUncle);
        }
        if (parents.Father is not null)
        {
            LabelSideAuntsUncles(parents.Father, graph, labels, RelativeType.PaternalAunt, RelativeType.PaternalUncle);
        }
    }

    private static void LabelSideAuntsUncles(
        string parentId,
        Graph graph,
        Dictionary<string, RelativeType> labels,
        RelativeType auntLabel,
        RelativeType uncleLabel)
    {
        if (!graph.ParentCoupleOfChild.TryGetValue(parentId, out var parentCouple)) return;
        if (!graph.ChildrenByCouple.TryGetValue(parentCouple, out var siblings)) return;
        foreach (var siblingId in siblings)
        {
            if (siblingId == parentId || labels.ContainsKey(siblingId)) continue;
            if (!graph.IndividualsById.TryGetValue(siblingId, out var sibling)) continue;
            labels[siblingId] = sibling.BiologicalSex == BiologicalSex.Male ? uncleLabel : auntLabel;
        }
    }

    private static void LabelNiecesAndNephews(Graph graph, Dictionary<string, RelativeType> labels)
    {
        foreach (var (id, label) in labels.ToList())
        {
            if (label != RelativeType.Brother && label != RelativeType.Sister &&
                label != RelativeType.HalfBrother && label != RelativeType.HalfSister)
            {
                continue;
            }
            if (!graph.CouplesByPartner.TryGetValue(id, out var couples)) continue;
            foreach (var coupleId in couples)
            {
                if (!graph.ChildrenByCouple.TryGetValue(coupleId, out var children)) continue;
                foreach (var childId in children)
                {
                    if (labels.ContainsKey(childId)) continue;
                    if (!graph.IndividualsById.TryGetValue(childId, out var child)) continue;
                    labels[childId] = child.BiologicalSex == BiologicalSex.Male
                        ? RelativeType.Nephew : RelativeType.Niece;
                }
            }
        }
    }

    private static void LabelFirstCousins(Graph graph, Dictionary<string, RelativeType> labels)
    {
        foreach (var (id, label) in labels.ToList())
        {
            if (label != RelativeType.MaternalAunt && label != RelativeType.MaternalUncle &&
                label != RelativeType.PaternalAunt && label != RelativeType.PaternalUncle)
            {
                continue;
            }
            if (!graph.CouplesByPartner.TryGetValue(id, out var couples)) continue;
            foreach (var coupleId in couples)
            {
                if (!graph.ChildrenByCouple.TryGetValue(coupleId, out var children)) continue;
                foreach (var childId in children)
                {
                    if (labels.ContainsKey(childId)) continue;
                    labels[childId] = RelativeType.FirstCousin;
                }
            }
        }
    }
}
