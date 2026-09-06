using System.Text.Json;
using System.Text.Json.Nodes;

namespace HondaEcu.Core.Tests;

public sealed class P28NativeChecksumVerifierTests
{
    [Fact]
    public async Task AnInventedBindingDoesNotMakeArbitraryBytesARecognizedNativeAlgorithm()
    {
        var (image, profile, binding) = Fixture();
        var before = image.ToArray();
        var report = await P28NativeChecksumVerifier.CheckAsync(image, profile, binding, true);
        var item = Assert.Single(report.Cases);
        Assert.Equal(NativeChecksumDisposition.UnsupportedRevision, item.Disposition);
        Assert.Equal(ChecksumStatus.Unknown, item.ChecksumStatus);
        Assert.True(item.Arithmetic.ResidueMatches);
        Assert.All(item.Execution, execution => Assert.Equal(NativeChecksumExecutionStatus.NotRun, execution.Status));
        Assert.False(report.RepairPerformed);
        Assert.Equal(FlashSafetyStatus.NotFlashReady, report.FlashSafety);
        Assert.Equal(before, image.ToArray());
        Assert.Null(report.Contract.StoredChecksumOffset);
        Assert.Contains("Unresolved/Unsupported", report.Evidence, StringComparison.Ordinal);
    }

    [Fact]
    public async Task ExistingAdmissionAndOneParentLineageRemainMandatory()
    {
        var (image, profile, binding) = Fixture();
        await Assert.ThrowsAsync<InvalidDataException>(() => P28NativeChecksumVerifier.CheckAsync(image, profile, binding, false));
        var changed = image.CreateModifiedCopy([new BytePatch(8, new byte[] { 1 })]);
        await Assert.ThrowsAsync<InvalidDataException>(() => P28NativeChecksumVerifier.CheckAsync(changed, profile, binding, true));
        await Assert.ThrowsAsync<InvalidDataException>(() => P28NativeChecksumVerifier.CheckAsync(image, profile, binding, true, derived: changed));
        var plan = P28RawThresholdEditor.CreatePlan(image, profile, binding, true, P28ThresholdLogic.GetSlots()[0].Id, 1);
        var child = P28RawThresholdEditor.Apply(image, profile, binding, plan);
        var report = await P28NativeChecksumVerifier.CheckAsync(image, profile, binding, true, derived: child.Image, plan: plan, patchReport: child.Report);
        Assert.True(report.VerifiedDerivedLineage);
        Assert.Equal(binding.RomHash, report.BaselineHash);
        Assert.NotEqual(binding.RomHash, report.DerivedHash);
        Assert.Equal((byte)1, report.Cases[1].Arithmetic.ComputedResult);
        Assert.All(report.Cases, item => Assert.Equal(ChecksumStatus.Unknown, item.ChecksumStatus));
    }

    [Theory]
    [InlineData(NativeChecksumExecutionStatus.ConditionalMatch)]
    [InlineData(NativeChecksumExecutionStatus.UnresolvedInstruction)]
    [InlineData(NativeChecksumExecutionStatus.Mismatch)]
    [InlineData(NativeChecksumExecutionStatus.ExecutionError)]
    [InlineData(NativeChecksumExecutionStatus.BudgetExceeded)]
    [InlineData(NativeChecksumExecutionStatus.Incomplete)]
    public void UnestablishedExecutionNeverBecomesUnconditionalValid(NativeChecksumExecutionStatus status)
    {
        // Fabricated status-mapping inputs only, not a recognized OEM program.
        var code = new P28ChecksumCodeAssessment(true, true, NativeChecksumDisposition.Unknown, [], "Synthetic mapping fixture");
        var arithmetic = P28NativeChecksumArithmetic.Calculate(RomImage.FromBytes(new byte[32768]));
        var result = P28NativeChecksumVerifier.Decide(code, arithmetic, [Observation(status)]);
        Assert.Equal(ChecksumStatus.Unknown, result.Status);
    }

    [Fact]
    public void MissingExecutionDoesNotEraseIndependentArithmeticAndDisabledIsNeverValid()
    {
        var arithmetic = P28NativeChecksumArithmetic.Calculate(RomImage.FromBytes(new byte[32768]));
        var recognized = new P28ChecksumCodeAssessment(true, true, NativeChecksumDisposition.Unknown, [], "Synthetic mapping fixture");
        Assert.Equal(ChecksumStatus.Valid, P28NativeChecksumVerifier.Decide(recognized, arithmetic, [Observation(NativeChecksumExecutionStatus.NotRun)]).Status);
        var disabled = recognized with { GateEnabled = false, Disposition = NativeChecksumDisposition.DisabledOrAltered };
        Assert.Equal(ChecksumStatus.Unknown, P28NativeChecksumVerifier.Decide(disabled, arithmetic, [Observation(NativeChecksumExecutionStatus.Match)]).Status);
        Assert.Throws<ArgumentException>(() => P28NativeChecksumVerifier.ValidateAssumptions([P28ByteExecutionValidator.AddAssumption]));
        Assert.Throws<ArgumentException>(() => P28NativeChecksumVerifier.ValidateAssumptions([P28ProducerModel.AddEr1Assumption]));
    }

    [Fact]
    public void MockCompletedResponseRequiresAll512StatesExactReadOrderAndRealisticSteps()
    {
        var image = RomImage.FromBytes(new byte[32768]);
        var root = CompleteModelResponse(image);
        Assert.Equal(NativeChecksumExecutionStatus.Match, P28NativeChecksumVerifier.CompareExecution(image, Element(root)).Status);
        root["checkpoints"]![100]!["sumAfter"] = 1;
        Assert.Equal(NativeChecksumExecutionStatus.Mismatch, P28NativeChecksumVerifier.CompareExecution(image, Element(root)).Status);
        root = CompleteModelResponse(image);
        root["programReadRuns"] = new JsonArray(new JsonArray(0, 32767), new JsonArray(0, 1));
        root["coverageRanges"] = new JsonArray(new JsonArray(0, 32767));
        Assert.Equal(NativeChecksumExecutionStatus.Mismatch, P28NativeChecksumVerifier.CompareExecution(image, Element(root)).Status);
        root = CompleteModelResponse(image);
        root["checkpoints"]![0]!["steps"] = 0;
        Assert.Throws<SliceProcessException>(() => P28NativeChecksumVerifier.CompareExecution(image, Element(root)));
        root = CompleteModelResponse(image);
        root["usedAssumptions"] = new JsonArray(P28ByteExecutionValidator.AddAssumption);
        Assert.Throws<SliceProcessException>(() => P28NativeChecksumVerifier.CompareExecution(image, Element(root)));
    }

    [Fact]
    public void IntermediateAndFailureReportsCannotClaimCompletionOrCoverageTheyDidNotObserve()
    {
        var image = RomImage.FromBytes(new byte[32768]);
        var root = CompleteModelResponse(image);
        root["completed"] = false;
        root["residue"] = -1;
        Assert.Equal(NativeChecksumExecutionStatus.Incomplete, P28NativeChecksumVerifier.CompareExecution(image, Element(root)).Status);
        root["status"] = 1;
        Assert.Equal(NativeChecksumExecutionStatus.UnresolvedInstruction, P28NativeChecksumVerifier.CompareExecution(image, Element(root)).Status);
        root["status"] = 2;
        Assert.Equal(NativeChecksumExecutionStatus.ExecutionError, P28NativeChecksumVerifier.CompareExecution(image, Element(root)).Status);
        root["status"] = 3;
        Assert.Equal(NativeChecksumExecutionStatus.BudgetExceeded, P28NativeChecksumVerifier.CompareExecution(image, Element(root)).Status);
        root["completed"] = true;
        Assert.Throws<SliceProcessException>(() => P28NativeChecksumVerifier.CompareExecution(image, Element(root)));
    }

    [Theory]
    [InlineData(0, 0)]
    [InlineData(1, 0)]
    [InlineData(1, 1)]
    public void MockCompletionPreservesResidueFailureGateAndRepeatedProgramRead(int value, int gate)
    {
        var bytes = new byte[32768]; bytes[0] = (byte)value; bytes[P28NativeChecksumArithmetic.GateOffset] = (byte)gate;
        var image = RomImage.FromBytes(bytes);
        var result = P28NativeChecksumVerifier.CompareExecution(image, Element(CompleteModelResponse(image)));
        Assert.Equal(NativeChecksumExecutionStatus.Match, result.Status);
        Assert.Equal(value + gate == 0 ? 32768 : 32769, result.ProgramReadCount);
        Assert.Equal(new ByteRange(0, 32768), Assert.Single(result.ActualCoverage));
    }

    [Fact]
    [Trait("Category", "RustIntegration")]
    public async Task ActualChecksumPolicyExecutesUnrelatedSyntheticProgramAndRejectsOtherWordAddForm()
    {
        // Independent toy: LC word program constant through seeded X1; ADDB A,DATA90;
        // ADDB r0,A. No OEM routine or reconstructed native fixture is used.
        async Task<JsonElement> Run(int constant, bool unknown = false)
        {
            int[] program = new int[0x122];
            (unknown ? new[] { 0x47, 0x81 } : new[] { 0x90, 0xA8, 0xC5, 0x90, 0x82, 0x20, 0x81 }).CopyTo(program, 0);
            program[0x120] = constant;
            var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner, new
            {
                protocolVersion = 1,
                operation = "checksumSynthetic",
                images = new[] { new { id = "invented-byte-add", rom = program } },
                allowAssumptions = Array.Empty<string>(),
                scratchPatterns = new[] { 85 },
                synthetic = new
                {
                    entryPc = 0,
                    exitPcs = new[] { unknown ? 2 : 7 },
                    allowedCodeRanges = new[] { new[] { 0, unknown ? 2 : 7 } },
                    psw = unknown ? 0x1100 : 0x0100,
                    lrb = 0x41,
                    usp = 0x180,
                    instructionBudget = 8,
                    dataSeeds = new[] { new[] { 0x90, 5 }, [0x208, 10], [0x120, 99], [0x80, 0x20], [0x81, 1] },
                    outputAddresses = new[] { 0x208 },
                },
            });
            Assert.Equal("0.7.0", response.Response.GetProperty("runnerVersion").GetString());
            return response.Response.GetProperty("syntheticResult").Clone();
        }
        var first = await Run(7);
        var changed = await Run(8);
        Assert.Equal(0, first.GetProperty("status").GetInt32());
        Assert.Equal(22, first.GetProperty("outputs")[0].GetInt32());
        Assert.Equal(23, changed.GetProperty("outputs")[0].GetInt32());
        Assert.Equal(new[] { 0x120, 0x121 }, first.GetProperty("programReads").EnumerateArray().Select(item => item.GetInt32()));
        Assert.Equal(1, (await Run(7, true)).GetProperty("status").GetInt32());
    }

    [Fact]
    [Trait("Category", "RustIntegration")]
    public async Task ActualChecksumBatchEarlyExitCannotPassAsOneSuccessfulCompleteInvocation()
    {
        var bytes = new byte[32768];
        // One invented unconditional jump; this is not the native checksum code.
        new byte[] { 3, 0xB6, 0x2B }.CopyTo(bytes, 0x2B70);
        var image = RomImage.FromBytes(bytes);
        var response = await SeededSliceProcess.ExchangeAsync(ExecutionTestPaths.RustRunner,
            P28NativeChecksumVerifier.CreateRequest(new[] { ("early-exit", image) }));
        Assert.Equal(3, response.Response.GetProperty("checksumCases").GetArrayLength());
        foreach (var row in response.Response.GetProperty("checksumCases").EnumerateArray())
        {
            var actual = P28NativeChecksumVerifier.CompareExecution(image, row);
            Assert.Equal(NativeChecksumExecutionStatus.ExecutionError, actual.Status);
            Assert.False(actual.Complete);
            Assert.Equal(0, actual.ProgramReadCount);
            Assert.False(actual.IntermediateStateMatches);
        }
    }

    private static P28ChecksumExecution Observation(NativeChecksumExecutionStatus status) =>
        new(0, status, status == NativeChecksumExecutionStatus.Match, null, null, 0, 0, null, 0, [], false, false, [], [], "Fabricated status mapping only");

    private static (RomImage Image, RomProfile Profile, P28ExactBaselineBinding Binding) Fixture()
    {
        var image = RomImage.FromBytes(new byte[32768]);
        var profile = new RomProfile("p28-304", "Synthetic checksum test profile", "Not an OEM firmware fixture", 32768, "Synthetic", true, true);
        var binding = new P28ExactBaselineBinding(1, P28CompactModel.ModelId, profile.Id, image.Size, image.Hash, P28VtecInspector.ComputeProfileDigest(profile));
        return (image, profile, binding);
    }

    private static JsonElement Element(JsonNode node) => JsonSerializer.SerializeToElement(node);

    private static JsonObject CompleteModelResponse(RomImage image)
    {
        // Mock protocol accounting only. This deliberately does not execute a ROM.
        var model = P28NativeChecksumArithmetic.Calculate(image);
        var failure = !model.ResidueMatches && image.Bytes.Span[P28NativeChecksumArithmetic.GateOffset] == 0;
        var finalSteps = model.ResidueMatches ? 208 : failure ? 213 : 211;
        var checkpoints = model.Checkpoints.Select((item, index) => new
        {
            invocation = index + 1,
            counterBefore = item.CounterBefore,
            counterAfter = item.CounterAfter,
            sumBefore = item.SumBefore,
            sumAfter = item.SumAfter,
            computedByte = item.ComputedByte,
            exitPc = index == 511 && failure ? 0x24E9 : 0x2BB6,
            steps = index == 511 ? finalSteps : 205,
            programReadCount = index == 511 && !model.ResidueMatches ? 65 : 64,
            programReadRuns = index == 511 && !model.ResidueMatches ? new[] { new[] { index * 64, 64 }, [P28NativeChecksumArithmetic.GateOffset, 1] } : new[] { new[] { index * 64, 64 } },
        });
        return JsonSerializer.SerializeToNode(new
        {
            imageIndex = 0,
            scratchPattern = 0,
            status = 0,
            completed = true,
            decision = model.ResidueMatches ? "ResidueZero" : failure ? "NonzeroResidueFailure" : "NonzeroResidueBypassed",
            invocations = 512,
            steps = 511 * 205 + finalSteps,
            stopPc = failure ? 0x24E9 : 0x2BB6,
            residue = model.ComputedResult,
            counter = 0,
            accumulatedByte = 0,
            statusByte = failure ? 0x48 : 0,
            programReadCount = model.ResidueMatches ? 32768 : 32769,
            programReadRuns = model.ResidueMatches ? new[] { new[] { 0, 32768 } } : new[] { new[] { 0, 32768 }, [P28NativeChecksumArithmetic.GateOffset, 1] },
            coverageRanges = new[] { new[] { 0, 32768 } },
            usedAssumptions = Array.Empty<string>(),
            checkpoints,
            trace = Array.Empty<object>(),
            error = (string?)null,
        })!.AsObject();
    }
}
