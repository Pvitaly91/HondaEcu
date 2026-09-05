using System.IO;
using HondaEcu.Core;
using HondaEcu.Desktop.Models;

namespace HondaEcu.Desktop.Tests;

public sealed class ChecksumPreservingDesktopTests
{
    [Theory]
    [InlineData("0", "0/216/0", "2")]
    [InlineData("40", "0/0/0", "0")]
    [InlineData("255", "0/215/0", "2")]
    public async Task DemoShowsSeparateInventedArithmeticAndNeverAuthorizesExecutionOrSave(string raw, string residues, string diff)
    {
        using var fixture = new DesktopFixture();
        var operations = new FakeOperations();
        using var model = fixture.CreateModel(operations);
        model.EnterDemo();
        model.ProposedRaw = raw;
        Assert.True(model.CanPreviewChecksumExport);
        model.PreviewChecksumExport();
        Assert.Contains("ОКРЕМИЙ вигаданий fixture", model.ChecksumExportPreview);
        Assert.Contains("compensation 0x7000", model.ChecksumExportPreview);
        Assert.Contains("Не поточні 8 байтів D0 demo", model.ChecksumExportPreview);
        Assert.Contains($"Residue A/B/C: {residues}", model.ChecksumExportPreview);
        Assert.Contains($"Фактичний diff: {diff}", model.ChecksumExportPreview);
        Assert.Contains("Actual execution: NotRun", model.ChecksumExportPreview);
        Assert.Contains("NotFlashReady", model.ChecksumExportPreview);
        Assert.False(model.CanValidateChecksumExport);
        Assert.False(model.CanSaveChecksumExport);
        Assert.False(model.CanSave);
        await model.ValidateChecksumExportAsync();
        await model.SaveChecksumExportAsync(fixture.OutputPaths);
        Assert.Equal(0, operations.ValidationCount);
        Assert.Equal(0, fixture.Dialogs.ConfirmationCount);
        Assert.False(File.Exists(fixture.OutputPaths.OutputPath));
    }

    [Theory]
    [InlineData("256")]
    [InlineData("-1")]
    [InlineData("40.0")]
    [InlineData("0x28")]
    [InlineData("")]
    public void DemoRejectsInvalidRawInputWithoutStalePreview(string raw)
    {
        using var fixture = new DesktopFixture();
        using var model = fixture.CreateModel();
        model.EnterDemo(); model.ProposedRaw = "41"; model.PreviewChecksumExport();
        model.ProposedRaw = raw; model.PreviewChecksumExport();
        Assert.NotEmpty(model.ErrorText);
        Assert.DoesNotContain("Residue A/B/C", model.ChecksumExportPreview);
        Assert.False(model.CanSaveChecksumExport);
    }

    [Theory]
    [InlineData("raw")]
    [InlineData("slot")]
    [InlineData("runner")]
    [InlineData("assumption")]
    [InlineData("demo")]
    public void EveryNewInputStateInvalidatesThePriorCompositionPreview(string action)
    {
        using var fixture = new DesktopFixture();
        using var model = fixture.CreateModel();
        model.EnterDemo(); model.ProposedRaw = "41"; model.PreviewChecksumExport();
        var session = model.SessionId;
        switch (action)
        {
            case "raw": model.ProposedRaw = "42"; break;
            case "slot": model.SelectedSlot = model.Slots[1]; break;
            case "runner": model.SelectRunner(fixture.RunnerPath); break;
            case "assumption": model.AllowAddEr1 = true; break;
            default: model.EnterDemo(); break;
        }
        Assert.True(model.SessionId > session);
        Assert.DoesNotContain("Residue A/B/C", model.ChecksumExportPreview);
        Assert.False(model.CanSaveChecksumExport);
        Assert.False(model.CanValidateChecksumExport);
    }

    [Fact]
    public async Task UnavailableOrForgedDefinitionDoesNotDisableOrSilentlyCompensateLegacyRawSave()
    {
        using var fixture = new DesktopFixture();
        using var model = await fixture.CreateBoundModel();
        Assert.False(model.CanPreviewChecksumExport);
        Assert.False(model.CanSaveChecksumExport);
        Assert.Contains("Недоступне", model.CompensationStatus);
        model.ProposedRaw = "45";
        model.PreviewChange();
        Assert.True(model.CanSave);
        var forged = Path.Combine(fixture.DirectoryPath, "untrusted-definition.json");
        File.WriteAllText(forged, "{\"candidateUnused\":true,\"offset\":32767}");
        model.SelectCompensationDefinition(forged);
        Assert.Contains("Недоступне", model.CompensationStatus);
        Assert.False(model.CanPreviewChecksumExport);
        Assert.False(model.CanSaveChecksumExport);
        Assert.True(model.CanSave);
        Assert.Equal(1, model.ChangedByteCount);
        await model.SaveCopyAsync(fixture.OutputPaths);
        var child = File.ReadAllBytes(fixture.OutputPaths.OutputPath);
        Assert.Equal(1, child.Zip(fixture.Bytes).Count(pair => pair.First != pair.Second));
        Assert.Equal(fixture.Bytes[0x7000], child[0x7000]);
        Assert.Equal(fixture.Bytes[0x7FFF], child[0x7FFF]);
        Assert.Equal(DesktopAccessMode.VerifiedDerived, model.Mode);
        Assert.False(model.CanSaveChecksumExport);
        Assert.Equal(fixture.Bytes, File.ReadAllBytes(fixture.ParentPath));
    }

    [Fact]
    public async Task MissingRunnerAndUnadmittedSourceStayPreviewOnlyWithoutInventingHondaAuthority()
    {
        using var fixture = new DesktopFixture();
        using var model = await fixture.CreateBoundModel();
        Assert.False(model.CanValidateChecksumExport);
        Assert.False(model.CanSaveChecksumExport);
        model.PreviewChecksumExport();
        await model.ValidateChecksumExportAsync();
        await model.SaveChecksumExportAsync(fixture.OutputPaths);
        Assert.False(File.Exists(fixture.OutputPaths.OutputPath));
        Assert.False(model.HasChecksumResult);
        await model.OpenBinAsync(fixture.SmallRaw);
        Assert.Equal(DesktopAccessMode.RawOnly, model.Mode);
        Assert.False(model.CanPreviewChecksumExport);
        Assert.False(model.SelectCompensationCommand.CanExecute(null));
    }

    [Theory]
    [InlineData(false)]
    [InlineData(true)]
    public async Task CanceledOrLateUnrelatedValidationCannotAttachExecutionToANewM1gPreview(bool changeSession)
    {
        using var fixture = new DesktopFixture();
        var operations = new FakeOperations { Block = true, IgnoreCancellation = true };
        using var model = await fixture.CreateBoundModel(operations);
        var work = model.RunValidationAsync(DesktopValidationKind.Checksum);
        await operations.Started.Task;
        if (changeSession) model.EnterDemo(); else model.Cancel();
        operations.Release.TrySetResult(); await work;
        Assert.True(operations.Token.IsCancellationRequested);
        Assert.False(model.IsBusy);
        Assert.False(model.CanSaveChecksumExport);
        Assert.False(model.OpenResultsCommand.CanExecute(null));
        Assert.Equal(DesktopCounters.Empty, model.Counters);
        model.EnterDemo(); model.ProposedRaw = "41"; model.PreviewChecksumExport();
        Assert.Contains("Actual execution: NotRun", model.ChecksumExportPreview);
        Assert.False(model.CanValidateChecksumExport);
        Assert.False(model.CanSaveChecksumExport);
    }

    [Fact]
    public async Task ExistingM1cChildRemainsOriginalParentLineageAndCannotGainExportByOpeningAReceiptClaim()
    {
        using var fixture = new DesktopFixture();
        fixture.SaveChild();
        using var model = fixture.CreateModel();
        await model.OpenDerivedAsync(fixture.OutputPaths.OutputPath, fixture.ParentPath, fixture.ProfilePath,
            fixture.BindingPath, fixture.OutputPaths.PlanPath, fixture.OutputPaths.ReportPath, true);
        Assert.Equal(DesktopAccessMode.VerifiedDerived, model.Mode);
        Assert.False(model.CanEdit);
        Assert.False(model.CanPreviewChecksumExport);
        var original = File.ReadAllBytes(fixture.ParentPath);
        await model.OpenChecksumChildAsync(fixture.OutputPaths.OutputPath, fixture.ParentPath, fixture.ProfilePath,
            fixture.BindingPath, fixture.OutputPaths.PlanPath, fixture.OutputPaths.ReportPath, fixture.BindingPath, true);
        Assert.NotEmpty(model.ErrorText);
        Assert.Equal(DesktopAccessMode.VerifiedDerived, model.Mode);
        Assert.False(model.CanSaveChecksumExport);
        Assert.Equal(original, File.ReadAllBytes(fixture.ParentPath));
    }
}
