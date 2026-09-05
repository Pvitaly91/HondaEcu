namespace HondaEcu.Desktop.Services;

public interface IDialogService
{
    string? OpenFile(string title, string filter);
    string? SaveFile(string title, string filter, string suggestedName);
    bool Confirm(string title, string message);
    void ShowMessage(string title, string message);
    void ShowStructuredResult(string title, string json);
}
