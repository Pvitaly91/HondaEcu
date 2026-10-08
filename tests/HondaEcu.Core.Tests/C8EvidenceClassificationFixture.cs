namespace HondaEcu.Core.Tests;

// Invented evidence-policy data only. These flags model a reviewer's verified
// inputs; this fixture cannot authenticate a source, observe silicon, execute a
// probe, or supply an ISA predicate to production code.
internal enum C8EvidenceClassification
{
    VendorConfirmed, IndependentCompatibleSiliconConfirmed, PrimaryDocumentClarification,
    SecondaryEvidenceOnly, InquiryDraftReady, PrimaryConflictUnresolved
}
internal enum C8EvidenceKind { VendorResponse, PrimaryCorrection, SiliconRecord, Secondary, InquiryDraft }
internal enum C8Applicability { Unknown, ExactMsm66201, IndependentExactC8Compatibility, AssemblyFamilySimilarity, OtherCore }
internal enum C8FlagProvenance { Unknown, NativeCmpObservation, HostFlags }
// These labels describe agreement at the three ordinary CMP states only, not
// the unreachable CF=ZF=1 state, a validated universal ISA predicate or a fix.
internal enum C8ReportedPredicate { NotEstablished, ReportedOr, ReportedAnd }

internal sealed record C8BranchObservation(ushort Left, ushort Right, bool? Cf, bool? Zf,
    C8FlagProvenance FlagProvenance, bool CmpInstructionAndOperandsVerified, bool FlagsUnchanged,
    string BinaryIdentity, bool BinaryBytesVerified, ushort BranchPc, byte Opcode, byte Displacement,
    string Condition, bool BranchTraceRecorded, bool DestinationIndependentlyVerified,
    bool ObservedTaken, ushort ObservedNextPc);

internal sealed record C8EvidenceWitness
{
    internal C8EvidenceKind Kind { get; init; }
    internal C8Applicability Applicability { get; init; }
    internal bool ApplicabilityVerified { get; init; }
    internal string ApplicabilityEvidenceIdentity { get; init; } = "";
    internal byte[] InstructionBytes { get; init; } = [];
    internal string Condition { get; init; } = "";
    internal bool SourceAuthenticated { get; init; }
    internal bool IndependentContent { get; init; }
    internal string ContentIdentity { get; init; } = "";
    internal string VisualIdentity { get; init; } = "";
    internal string Revision { get; init; } = "";
    internal bool RevisionVerified { get; init; }
    internal bool CorrectionExplicit { get; init; }
    internal bool VendorSiliconConfirmed { get; init; }
    internal bool QuotesOldTableOnly { get; init; }
    internal bool? ReportedEqualityTaken { get; init; }
    internal bool? ReportedLessTaken { get; init; }
    internal bool EmulatorOnly { get; init; }
    internal bool ExpectedFromExistingExecutor { get; init; }
    internal bool ClaimsActualRomExecution { get; init; }
    internal string MachineIdentity { get; init; } = "";
    internal bool MachineIdentityVerified { get; init; }
    internal string CapturedUtc { get; init; } = "";
    internal string CaptureMethod { get; init; } = "";
    internal string RawRecordIdentity { get; init; } = "";
    internal bool RecordingProvenanceVerified { get; init; }
    internal bool BinaryControlVerified { get; init; }
    internal bool ControlledDifferencesVerified { get; init; }
    internal IReadOnlyList<C8BranchObservation> Observations { get; init; } = [];
    internal bool InquiryDraftComplete { get; init; }
}

internal sealed record C8EvidenceDecision(C8EvidenceClassification Classification,
    C8ReportedPredicate ReportedPredicate, string Reason)
{
    internal int ActualRomExecutions => 0;
    internal string Scope => "InventedEvidencePolicyOnly";
    internal void RequireActualRomExecution() =>
        throw new InvalidDataException("Evidence classification is not an actual-ROM execution or an executor contract.");
}

internal static class C8EvidenceClassificationFixture
{
    internal const string OriginalContentIdentity = "invented-original-document-bytes";
    internal const string OriginalVisualIdentity = "invented-original-document-page";

    // Address arithmetic for an abstract two-byte branch, not instruction execution.
    internal static ushort RelativeTarget(ushort pc, byte displacement) =>
        unchecked((ushort)(pc + 2 + unchecked((sbyte)displacement)));

    internal static C8EvidenceDecision Classify(C8EvidenceWitness witness)
    {
        if (witness.ClaimsActualRomExecution) return Unresolved("An evidence record cannot be promoted to actual-ROM execution.");
        if (witness.Kind == C8EvidenceKind.InquiryDraft)
            return witness.InquiryDraftComplete
                ? new(C8EvidenceClassification.InquiryDraftReady, C8ReportedPredicate.NotEstablished, "Draft only; no sending or vendor response is implied.")
                : Unresolved("The inquiry draft is incomplete.");
        if (witness.Kind == C8EvidenceKind.Secondary || witness.EmulatorOnly)
            return new(C8EvidenceClassification.SecondaryEvidenceOnly, C8ReportedPredicate.NotEstablished, "Secondary or emulator-only evidence is not native silicon validation.");
        if (witness.ExpectedFromExistingExecutor) return Unresolved("The existing executor cannot be its own independent expectation.");
        if (!witness.SourceAuthenticated || !witness.IndependentContent ||
            string.IsNullOrWhiteSpace(witness.ContentIdentity)) return Unresolved("Independent source provenance is unverified.");
        if (!witness.ApplicabilityVerified || witness.Applicability is not
            (C8Applicability.ExactMsm66201 or C8Applicability.IndependentExactC8Compatibility) ||
            (witness.Applicability == C8Applicability.IndependentExactC8Compatibility &&
            string.IsNullOrWhiteSpace(witness.ApplicabilityEvidenceIdentity)))
            return Unresolved("Family or mnemonic similarity is not independent exact-C8 applicability.");
        if (witness.InstructionBytes.Length != 2 || witness.InstructionBytes[0] != 0xC8 || witness.Condition != "GT")
            return Unresolved("The evidence is not for the exact C8 rel8 GT condition.");
        if (!witness.RevisionVerified || string.IsNullOrWhiteSpace(witness.Revision))
            return Unresolved("The applicable device or document revision is unverified.");

        if (witness.Kind == C8EvidenceKind.PrimaryCorrection)
        {
            if (witness.ContentIdentity == OriginalContentIdentity || witness.VisualIdentity == OriginalVisualIdentity ||
                string.IsNullOrWhiteSpace(witness.VisualIdentity)) return Unresolved("A byte or visual duplicate is not a new correction.");
            if (!witness.CorrectionExplicit || witness.QuotesOldTableOnly)
                return Unresolved("An old-table quote or mnemonic list is not an explicit primary correction.");
            return DeclaredDecision(witness, C8EvidenceClassification.PrimaryDocumentClarification);
        }
        if (witness.Kind == C8EvidenceKind.VendorResponse)
        {
            if (!witness.VendorSiliconConfirmed || witness.QuotesOldTableOnly)
                return Unresolved("A vendor document quotation is not confirmation of produced-chip behavior.");
            return DeclaredDecision(witness, C8EvidenceClassification.VendorConfirmed);
        }
        if (witness.Kind != C8EvidenceKind.SiliconRecord) return Unresolved("Unknown evidence kind.");
        if (!witness.MachineIdentityVerified || string.IsNullOrWhiteSpace(witness.MachineIdentity))
            return Unresolved("The physical machine identity is unverified.");
        if (!witness.RecordingProvenanceVerified || string.IsNullOrWhiteSpace(witness.CaptureMethod) ||
            string.IsNullOrWhiteSpace(witness.RawRecordIdentity) || !witness.CapturedUtc.EndsWith('Z') ||
            !DateTimeOffset.TryParse(witness.CapturedUtc, System.Globalization.CultureInfo.InvariantCulture,
                System.Globalization.DateTimeStyles.None, out _)) return Unresolved("Native recording time, method or provenance is missing.");
        if (!witness.BinaryControlVerified || witness.Observations.Count == 0 ||
            witness.Observations.Select(o => o.BinaryIdentity).Distinct().Count() > 1 && !witness.ControlledDifferencesVerified)
            return Unresolved("The common binary or precisely controlled case differences are unverified.");

        var outcomes = new Dictionary<int, bool>();
        foreach (var observation in witness.Observations)
        {
            // CompareTo promises only a negative/zero/positive result, not -1/0/+1.
            // Group every operand distance by the same greater/equal/less relation.
            var relation = Math.Sign(observation.Left.CompareTo(observation.Right));
            if (observation.FlagProvenance != C8FlagProvenance.NativeCmpObservation ||
                !observation.CmpInstructionAndOperandsVerified || !observation.FlagsUnchanged ||
                observation.Cf != (relation < 0) || observation.Zf != (relation == 0))
                return Unresolved("Native CMP operands, captured CF/ZF or unchanged CMP-to-C8 flags are unverified.");
            if (observation.Opcode != 0xC8 || observation.Displacement != witness.InstructionBytes[1] || observation.Condition != "GT" ||
                !observation.BinaryBytesVerified || string.IsNullOrWhiteSpace(observation.BinaryIdentity))
                return Unresolved("The native instruction bytes, comparison condition or binary identity are unverified.");
            if (!observation.BranchTraceRecorded || !observation.DestinationIndependentlyVerified ||
                observation.ObservedNextPc != (observation.ObservedTaken
                    ? RelativeTarget(observation.BranchPc, observation.Displacement)
                    : unchecked((ushort)(observation.BranchPc + 2))))
                return Unresolved("A selected result without a verified native branch trace and destination is insufficient.");
            if (outcomes.TryGetValue(relation, out var previous) && previous != observation.ObservedTaken)
                return Unresolved("Conflicting native observations cannot be silently selected.");
            outcomes[relation] = observation.ObservedTaken;
        }
        if (!outcomes.TryGetValue(1, out var greater) || !greater ||
            !outcomes.TryGetValue(0, out var equal) || !outcomes.TryGetValue(-1, out var less))
            return Unresolved("Greater alone is not decisive; consistent greater, equality and less controls are required.");
        var predicate = ReportedPredicate(equal, less);
        return predicate == C8ReportedPredicate.NotEstablished
            ? Unresolved("The equality and less observations do not resolve the two disputed formulas consistently.")
            : new(C8EvidenceClassification.IndependentCompatibleSiliconConfirmed, predicate,
                "Invented policy inputs meet the independently applicable native silicon-record requirements.");
    }

    private static C8EvidenceDecision DeclaredDecision(C8EvidenceWitness witness, C8EvidenceClassification classification)
    {
        var predicate = ReportedPredicate(witness.ReportedEqualityTaken, witness.ReportedLessTaken);
        return predicate == C8ReportedPredicate.NotEstablished
            ? Unresolved("Both equality and less behavior must be explicit and consistent with a disputed formula.")
            : new(classification, predicate, "Explicit, independently applicable scoped declaration; no actual-ROM execution is implied.");
    }

    private static C8ReportedPredicate ReportedPredicate(bool? equal, bool? less) => (equal, less) switch
    {
        (true, true) => C8ReportedPredicate.ReportedOr,
        (false, false) => C8ReportedPredicate.ReportedAnd,
        _ => C8ReportedPredicate.NotEstablished
    };

    private static C8EvidenceDecision Unresolved(string reason) =>
        new(C8EvidenceClassification.PrimaryConflictUnresolved, C8ReportedPredicate.NotEstablished, reason);

    internal static C8EvidenceWitness InventedDeclaration(C8EvidenceKind kind, bool taken) => new()
    {
        Kind = kind,
        Applicability = C8Applicability.ExactMsm66201,
        ApplicabilityVerified = true,
        InstructionBytes = [0xC8, 0x04],
        Condition = "GT",
        SourceAuthenticated = true,
        IndependentContent = true,
        ContentIdentity = "invented-independent-source",
        VisualIdentity = "invented-corrected-page",
        Revision = "invented-reviewed-revision-A",
        RevisionVerified = true,
        CorrectionExplicit = true,
        VendorSiliconConfirmed = true,
        ReportedEqualityTaken = taken,
        ReportedLessTaken = taken
    };

    internal static C8EvidenceWitness InventedSiliconRecord(bool taken) => InventedDeclaration(C8EvidenceKind.SiliconRecord, taken) with
    {
        MachineIdentity = "invented-independent-machine-A",
        MachineIdentityVerified = true,
        CapturedUtc = "2000-01-01T00:00:00Z",
        CaptureMethod = "invented-nonmutating-native-trace",
        RawRecordIdentity = "invented-native-record-A",
        RecordingProvenanceVerified = true,
        BinaryControlVerified = true,
        Observations = [InventedObservation(0x32, 0x31, true), InventedObservation(0x31, 0x31, taken), InventedObservation(0x30, 0x31, taken)]
    };

    private static C8BranchObservation InventedObservation(ushort left, ushort right, bool taken) =>
        new(left, right, left < right, left == right, C8FlagProvenance.NativeCmpObservation, true, true,
            "invented-probe-binary-A", true, 0x1200, 0xC8, 0x04, "GT", true, true, taken, (ushort)(taken ? 0x1206 : 0x1202));
}
