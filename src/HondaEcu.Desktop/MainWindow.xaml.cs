using System.ComponentModel;
using System.Windows;
using HondaEcu.Desktop.Services;
using HondaEcu.Desktop.ViewModels;

namespace HondaEcu.Desktop;

public partial class MainWindow : Window
{
    private bool closeAllowed;
    private bool closeRequested;

    public MainWindow()
    {
        InitializeComponent();
        // WPF sizes are device-independent units; clamp to the actual working
        // area so the first window fits on 100%, 125% and 150% displays.
        var availableWidth = Math.Max(480, SystemParameters.WorkArea.Width - 40);
        var availableHeight = Math.Max(420, SystemParameters.WorkArea.Height - 40);
        MinWidth = Math.Min(MinWidth, availableWidth);
        MinHeight = Math.Min(MinHeight, availableHeight);
        Width = Math.Min(Width, availableWidth);
        Height = Math.Min(Height, availableHeight);
        DataContext = new MainViewModel(new DesktopDialogService(this));
    }

    private async void Window_Closing(object? sender, CancelEventArgs e)
    {
        if (closeAllowed)
        {
            return;
        }
        e.Cancel = true;
        if (closeRequested)
        {
            return;
        }
        closeRequested = true;
        IsEnabled = false;
        try
        {
            if (DataContext is MainViewModel viewModel)
            {
                // Await the service's cancellation/child-process cleanup before
                // ending the dispatcher; no ROM or process logic lives here.
                await viewModel.RequestCloseAsync();
                viewModel.Dispose();
            }
            closeAllowed = true;
            // Even an already-completed cleanup must let the first Closing
            // event unwind before a second Close enters WPF's close pipeline.
            _ = Dispatcher.BeginInvoke(new Action(Close));
        }
        catch (Exception exception)
        {
            closeRequested = false;
            IsEnabled = true;
            MessageBox.Show(this, $"Не вдалося завершити операцію: {exception.Message}",
                "Завершення роботи", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }
}
