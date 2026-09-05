using System.Globalization;
using System.Runtime.ExceptionServices;
using System.Windows;
using System.Windows.Automation;
using System.Windows.Controls;
using System.Windows.Media;
using HondaEcu.Desktop.Controls;
using HondaEcu.Desktop.ViewModels;

namespace HondaEcu.Desktop.Tests;

public sealed class DesktopLayoutTests
{
    [Fact]
    public void SyntheticWindowMeasuresAt100125150PercentEquivalentViewportsWithoutClippingButtons()
    {
        Exception? failure = null;
        var stage = "starting STA thread";
        var thread = new Thread(() =>
        {
            try
            {
                stage = "creating application";
                var application = new App { ShutdownMode = ShutdownMode.OnExplicitShutdown };
                application.InitializeComponent();
                stage = "creating window";
                var window = new MainWindow();
                var viewModel = Assert.IsType<MainViewModel>(window.DataContext);
                viewModel.EnterDemo();
                viewModel.ProposedRaw = "60";
                viewModel.PreviewChange();
                var content = Assert.IsAssignableFrom<FrameworkElement>(window.Content);
                var tabs = Descendants<TabControl>(content).Single();
                foreach (var scale in new[] { 1.0, 1.25, 1.5 })
                {
                    stage = $"measuring viewport {scale}";
                    // Offscreen DIP measurement, not an OS DPI switch or GUI
                    // smoke test. Real window automation is recorded separately.
                    var viewport = new Size(1280 / scale, 900 / scale);
                    foreach (var tabIndex in new[] { 0, 1 })
                    {
                        tabs.SelectedIndex = tabIndex;
                        content.Measure(viewport);
                        content.Arrange(new Rect(viewport));
                        content.UpdateLayout();
                        foreach (var button in Descendants<Button>(content).Where(item => item.ActualWidth > 0))
                        {
                            Assert.True(button.ActualWidth <= viewport.Width, $"Button exceeds viewport: {button.Content}");
                            if (button.Content is not string label) continue;
                            var text = new FormattedText(label.Replace("_", "", StringComparison.Ordinal),
                                CultureInfo.GetCultureInfo("uk-UA"), FlowDirection.LeftToRight,
                                new Typeface(button.FontFamily, button.FontStyle, button.FontWeight, button.FontStretch),
                                button.FontSize, Brushes.Black, 1);
                            Assert.True(button.ActualWidth + 2 >= text.WidthIncludingTrailingWhitespace + button.Padding.Left + button.Padding.Right,
                                $"Button label clipped at {scale}: {label}");
                        }
                    }
                }
                var input = Assert.IsType<TextBox>(window.FindName("RawValueInput"));
                Assert.True(input.IsTabStop);
                Assert.False(string.IsNullOrWhiteSpace(AutomationProperties.GetName(input)));
                var table = Assert.IsType<DataGrid>(window.FindName("SlotTable"));
                Assert.True(table.IsReadOnly);
                Assert.Equal(8, table.Items.Count);
                Assert.True(table.Columns[0].MinWidth >= 285);
                var plot = Assert.IsType<PredicatePlot>(window.FindName("PredicatePlot"));
                plot.GetBindingExpression(PredicatePlot.RowsProperty)!.UpdateTarget();
                Assert.Same(viewModel.PlotRows, plot.Rows);
                Assert.Equal(256, plot.Rows!.Count);
                Assert.Contains(plot.Rows, row => row.Before != row.After);
                Assert.False(viewModel.CanSave);
                stage = "closing window";
                viewModel.Dispose();
                window.Close();
                // Process the deferred second Close and any layout work. This
                // does not show a window or substitute for a real GUI smoke test.
                window.Dispatcher.Invoke(System.Windows.Threading.DispatcherPriority.ApplicationIdle, new Action(() => { }));
                stage = "shutting down application";
                application.Shutdown();
                stage = "finished";
            }
            catch (Exception exception)
            {
                failure = exception;
            }
        })
        { IsBackground = true };
        thread.SetApartmentState(ApartmentState.STA);
        thread.Start();
        Assert.True(thread.Join(TimeSpan.FromSeconds(30)), $"STA layout measurement did not finish: {stage}.");
        if (failure is not null) ExceptionDispatchInfo.Capture(failure).Throw();
    }

    private static IEnumerable<T> Descendants<T>(DependencyObject parent) where T : DependencyObject
    {
        for (var index = 0; index < VisualTreeHelper.GetChildrenCount(parent); index++)
        {
            var child = VisualTreeHelper.GetChild(parent, index);
            if (child is T value) yield return value;
            foreach (var descendant in Descendants<T>(child)) yield return descendant;
        }
    }
}
