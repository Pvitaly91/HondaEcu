using System.Runtime.InteropServices;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using Microsoft.Win32;

namespace HondaEcu.Desktop.Services;

/// <summary>Native file/confirmation dialogs; all file safety decisions remain in services/Core.</summary>
public sealed class DesktopDialogService(Window owner) : IDialogService
{
    public string? OpenFile(string title, string filter)
    {
        var dialog = new OpenFileDialog
        {
            Title = title,
            Filter = filter,
            CheckFileExists = true,
            CheckPathExists = true,
            Multiselect = false,
        };
        return dialog.ShowDialog(owner) == true ? dialog.FileName : null;
    }

    public string? SaveFile(string title, string filter, string suggestedName)
    {
        var dialog = new SaveFileDialog
        {
            Title = title,
            Filter = filter,
            FileName = suggestedName,
            CheckPathExists = true,
            AddExtension = true,
            OverwritePrompt = true,
        };
        return dialog.ShowDialog(owner) == true ? dialog.FileName : null;
    }

    public bool Confirm(string title, string message) => MessageBox.Show(owner, message, title,
        MessageBoxButton.YesNo, MessageBoxImage.Warning, MessageBoxResult.No) == MessageBoxResult.Yes;

    public void ShowMessage(string title, string message) => MessageBox.Show(owner, message, title,
        MessageBoxButton.OK, MessageBoxImage.Information);

    public void ShowStructuredResult(string title, string json)
    {
        var resultWindow = new Window
        {
            Title = title,
            Owner = owner,
            Width = Math.Min(1000, SystemParameters.WorkArea.Width - 48),
            Height = Math.Min(720, SystemParameters.WorkArea.Height - 48),
            MinWidth = 480,
            MinHeight = 320,
            WindowStartupLocation = WindowStartupLocation.CenterOwner,
        };
        var layout = new DockPanel { Margin = new Thickness(16) };
        var heading = new TextBlock
        {
            Text = "Структурований результат цього запуску · лише читання",
            TextWrapping = TextWrapping.Wrap,
            FontSize = 17,
            FontWeight = FontWeights.SemiBold,
            Margin = new Thickness(0, 0, 0, 12),
        };
        DockPanel.SetDock(heading, Dock.Top);
        layout.Children.Add(heading);
        var actions = new WrapPanel { Margin = new Thickness(0, 12, 0, 0) };
        DockPanel.SetDock(actions, Dock.Bottom);
        var copyButton = new Button { Content = "_Скопіювати JSON" };
        copyButton.Click += (_, _) =>
        {
            try
            {
                Clipboard.SetText(json);
            }
            catch (ExternalException)
            {
                MessageBox.Show(resultWindow, "Буфер обміну зайнятий іншою програмою. Спробуйте ще раз.",
                    "Копіювання", MessageBoxButton.OK, MessageBoxImage.Information);
            }
        };
        actions.Children.Add(copyButton);
        var closeButton = new Button { Content = "_Закрити", IsCancel = true };
        closeButton.Click += (_, _) => resultWindow.Close();
        actions.Children.Add(closeButton);
        layout.Children.Add(actions);
        var text = new TextBox
        {
            Text = json,
            IsReadOnly = true,
            AcceptsReturn = true,
            AcceptsTab = true,
            FontFamily = new FontFamily("Consolas"),
            FontSize = 13,
            TextWrapping = TextWrapping.NoWrap,
            VerticalScrollBarVisibility = ScrollBarVisibility.Auto,
            HorizontalScrollBarVisibility = ScrollBarVisibility.Auto,
        };
        System.Windows.Automation.AutomationProperties.SetName(text, "JSON результату поточного запуску");
        layout.Children.Add(text);
        resultWindow.Content = layout;
        // The user explicitly opened this immutable snapshot. Keep its owner
        // blocked until it closes, so it cannot masquerade as a newer session.
        resultWindow.ShowDialog();
    }
}
