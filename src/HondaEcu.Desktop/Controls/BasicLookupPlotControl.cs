using System.Globalization;
using System.Windows;
using System.Windows.Media;
using HondaEcu.Desktop.ViewModels;

namespace HondaEcu.Desktop.Controls;

/// <summary>Draws precomputed Core integer values without interpolation or smoothing in WPF.</summary>
public sealed class BasicLookupPlotControl : FrameworkElement
{
    public static readonly DependencyProperty PlotProperty = DependencyProperty.Register(nameof(Plot), typeof(BasicLookupPlot), typeof(BasicLookupPlotControl),
        new FrameworkPropertyMetadata(null, FrameworkPropertyMetadataOptions.AffectsRender));
    public BasicLookupPlot? Plot { get => (BasicLookupPlot?)GetValue(PlotProperty); set => SetValue(PlotProperty, value); }
    protected override void OnRender(DrawingContext dc)
    {
        base.OnRender(dc);
        if (Plot is not { } plot || plot.Original.Count != 256 || plot.Requested.Count != 256 || ActualWidth < 150 || ActualHeight < 100) return;
        var area = new Rect(62, 18, ActualWidth - 80, ActualHeight - 50);
        var min = Math.Min(plot.Original.Min(), plot.Requested.Min()); var max = Math.Max(plot.Original.Max(), plot.Requested.Max());
        Point P(int x, int y) => new(area.Left + x * area.Width / 255, area.Bottom - (y - min) * area.Height / Math.Max(1, max - min));
        dc.DrawRectangle(Brushes.White, new Pen(Brushes.Gray, 1), area);
        void Label(string text, Point at) => dc.DrawText(new FormattedText(text, CultureInfo.InvariantCulture, FlowDirection.LeftToRight,
            new Typeface("Segoe UI"), 12, Brushes.Black, 1), at);
        Label(min.ToString(CultureInfo.InvariantCulture), new(0, area.Bottom - 12)); Label(max.ToString(CultureInfo.InvariantCulture), new(0, area.Top));
        foreach (var x in new[] { 0, 64, 128, 192, 255 }) Label(x.ToString(CultureInfo.InvariantCulture), new(P(x, min).X - 8, area.Bottom + 5));
        foreach (var (values, brush) in new[] { (plot.Original, Brushes.SteelBlue), (plot.Requested, Brushes.DarkOrange) })
        {
            var pen = new Pen(brush, 1.4);
            for (var x = 1; x < 256; x++)
            {
                dc.DrawLine(pen, P(x - 1, values[x - 1]), P(x, values[x - 1]));
                dc.DrawLine(pen, P(x, values[x - 1]), P(x, values[x]));
            }
            foreach (var x in plot.Axes) dc.DrawEllipse(brush, null, P(x, values[x]), 3, 3);
        }
    }
}
