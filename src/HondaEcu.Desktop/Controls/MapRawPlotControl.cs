using System.Globalization;
using System.Windows;
using System.Windows.Media;
using HondaEcu.Desktop.ViewModels;

namespace HondaEcu.Desktop.Controls;

/// <summary>Raw selected-row values only; Core owns lookup interpolation and multipliers.</summary>
public sealed class MapRawPlotControl : FrameworkElement
{
    public static readonly DependencyProperty PlotProperty = DependencyProperty.Register(nameof(Plot), typeof(BasicLookupPlot), typeof(MapRawPlotControl),
        new FrameworkPropertyMetadata(null, FrameworkPropertyMetadataOptions.AffectsRender));
    public BasicLookupPlot? Plot { get => (BasicLookupPlot?)GetValue(PlotProperty); set => SetValue(PlotProperty, value); }
    protected override void OnRender(DrawingContext dc)
    {
        base.OnRender(dc);
        if (Plot is not { Original.Count: 10, Requested.Count: 10 } plot || ActualWidth < 150 || ActualHeight < 100) return;
        var area = new Rect(48, 12, ActualWidth - 63, ActualHeight - 42);
        dc.DrawRectangle(Brushes.White, new Pen(Brushes.Gray, 1), area);
        Point At(int column, int value) => new(area.Left + column * area.Width / 9, area.Bottom - value * area.Height / 255);
        foreach (var (values, brush) in new[] { (plot.Original, Brushes.SteelBlue), (plot.Requested, Brushes.DarkOrange) })
        {
            var pen = new Pen(brush, 1.5);
            for (var i = 0; i < 10; i++)
            {
                dc.DrawEllipse(brush, null, At(i, values[i]), 3, 3);
                if (i != 0) dc.DrawLine(pen, At(i - 1, values[i - 1]), At(i, values[i]));
            }
        }
        void Label(string text, Point at) => dc.DrawText(new FormattedText(text, CultureInfo.InvariantCulture, FlowDirection.LeftToRight,
            new Typeface("Segoe UI"), 11, Brushes.Black, 1), at);
        Label("255", new(0, area.Top)); Label("0", new(15, area.Bottom - 10));
        for (var i = 0; i < 10; i++) Label(i.ToString(CultureInfo.InvariantCulture), new(At(i, 0).X - 4, area.Bottom + 5));
    }
}
