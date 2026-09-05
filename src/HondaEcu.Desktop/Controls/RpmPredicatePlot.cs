using System.Globalization;
using System.Windows;
using System.Windows.Automation.Peers;
using System.Windows.Media;

namespace HondaEcu.Desktop.Controls;

/// <summary>Display-only coordinates from exact Core regions. Never used for selection.</summary>
public sealed record RpmPlotRegion(double Lower, double Upper, bool LowerIncluded, bool UpperIncluded, string Classification);

/// <summary>Unsmoothed categorical steps; unknown/invalid/mixed have distinct lanes, not boolean values.</summary>
public sealed class RpmPredicatePlot : FrameworkElement
{
    public static readonly DependencyProperty RowsProperty = DependencyProperty.Register(nameof(Rows),
        typeof(IReadOnlyList<RpmPlotRegion>), typeof(RpmPredicatePlot),
        new FrameworkPropertyMetadata(null, FrameworkPropertyMetadataOptions.AffectsRender));
    public static readonly DependencyProperty CaptionProperty = DependencyProperty.Register(nameof(Caption),
        typeof(string), typeof(RpmPredicatePlot), new FrameworkPropertyMetadata("", FrameworkPropertyMetadataOptions.AffectsRender));
    public IReadOnlyList<RpmPlotRegion>? Rows
    {
        get => (IReadOnlyList<RpmPlotRegion>?)GetValue(RowsProperty);
        set => SetValue(RowsProperty, value);
    }
    public string Caption { get => (string)GetValue(CaptionProperty); set => SetValue(CaptionProperty, value); }

    protected override AutomationPeer OnCreateAutomationPeer() => new RpmPlotAutomationPeer(this);
    protected override void OnRender(DrawingContext context)
    {
        base.OnRender(context);
        context.DrawRectangle(Brushes.White, null, new Rect(RenderSize));
        if (ActualWidth < 220 || ActualHeight < 220 || Rows is not { Count: > 0 } rows) return;
        var lower = rows.Min(row => row.Lower);
        var upper = rows.Max(row => row.Upper);
        if (!double.IsFinite(lower) || !double.IsFinite(upper) || upper <= lower) return;
        var area = new Rect(85, 58, ActualWidth - 108, ActualHeight - 125);
        Text("Умовний RPM — ступінчастий математичний envelope", 0, 0, 14);
        Text(Caption, 0, 23, 12);
        var names = new[] { "AllTrue", "Mixed", "Unknown", "Invalid", "AllFalse" };
        for (var index = 0; index < names.Length; index++)
        {
            var y = Y(names[index]);
            context.DrawLine(new Pen(Brushes.LightGray, 1), new Point(area.Left, y), new Point(area.Right, y));
            Text(names[index], 0, y - 9, 12);
        }
        foreach (var row in rows)
        {
            var x1 = X(row.Lower); var x2 = X(row.Upper); var y = Y(row.Classification);
            var brush = row.Classification switch
            {
                "AllTrue" or "AllFalse" => Brushes.SteelBlue,
                "Mixed" => Brushes.DarkOrange,
                "Unknown" => Brushes.MediumPurple,
                _ => Brushes.IndianRed,
            };
            if (row.Classification is not ("AllTrue" or "AllFalse"))
                context.DrawRectangle(new SolidColorBrush(Color.FromArgb(25, 125, 80, 80)), null,
                    new Rect(x1, area.Top - 10, Math.Max(1, x2 - x1), area.Height + 20));
            context.DrawLine(new Pen(brush, 3), new Point(x1, y), new Point(x2, y));
            context.DrawEllipse(row.LowerIncluded ? brush : Brushes.White, new Pen(brush, 1.5), new Point(x1, y), 3.5, 3.5);
            context.DrawEllipse(row.UpperIncluded ? brush : Brushes.White, new Pen(brush, 1.5), new Point(x2, y), 3.5, 3.5);
        }
        for (var tick = 0; tick <= 4; tick++)
        {
            var value = lower + (upper - lower) * tick / 4;
            Text(value.ToString("G6", CultureInfo.InvariantCulture), X(value) - 22, area.Bottom + 18, 11);
        }
        Text("RPM (округлено лише для графіка). Точні N/D та відкриті/закриті межі — у таблиці/JSON.",
            0, area.Bottom + 42, 11);
        double X(double value) => area.Left + (value - lower) / (upper - lower) * area.Width;
        double Y(string state) => area.Top + Math.Max(0, Array.IndexOf(names, state)) * area.Height / 4;
        void Text(string value, double x, double y, double size)
        {
            var text = new FormattedText(value, CultureInfo.GetCultureInfo("uk-UA"), FlowDirection.LeftToRight,
                new Typeface("Segoe UI"), size, Brushes.DarkSlateGray, VisualTreeHelper.GetDpi(this).PixelsPerDip)
            { MaxTextWidth = Math.Max(20, ActualWidth - Math.Max(0, x)), Trimming = TextTrimming.CharacterEllipsis };
            context.DrawText(text, new Point(Math.Max(0, x), y));
        }
    }
    private sealed class RpmPlotAutomationPeer(RpmPredicatePlot owner) : FrameworkElementAutomationPeer(owner)
    {
        protected override string GetClassNameCore() => nameof(RpmPredicatePlot);
        protected override AutomationControlType GetAutomationControlTypeCore() => AutomationControlType.Image;
        protected override string GetHelpTextCore() => "Conditional calculation only. Exact interval topology is in the associated report. Mixed, Unknown and Invalid are not boolean or probability results.";
    }
}
