using System.Globalization;
using System.Windows;
using System.Windows.Automation.Peers;
using System.Windows.Media;
using HondaEcu.Core;

namespace HondaEcu.Desktop.Controls;

/// <summary>Draws immutable Core truth-table rows; never calculates a threshold predicate.</summary>
public sealed class PredicatePlot : FrameworkElement
{
    public static readonly DependencyProperty RowsProperty = DependencyProperty.Register(
        nameof(Rows), typeof(IReadOnlyList<P28PredicateRow>), typeof(PredicatePlot),
        new FrameworkPropertyMetadata(null, FrameworkPropertyMetadataOptions.AffectsRender));

    public IReadOnlyList<P28PredicateRow>? Rows
    {
        get => (IReadOnlyList<P28PredicateRow>?)GetValue(RowsProperty);
        set => SetValue(RowsProperty, value);
    }

    protected override AutomationPeer OnCreateAutomationPeer() => new PlotAutomationPeer(this);

    protected override void OnRender(DrawingContext drawingContext)
    {
        base.OnRender(drawingContext);
        if (ActualWidth < 180 || ActualHeight < 160)
        {
            return;
        }
        var area = new Rect(44, 50, ActualWidth - 64, ActualHeight - 110);
        drawingContext.DrawRectangle(Brushes.White, null, new Rect(RenderSize));
        var oldBrush = new SolidColorBrush(Color.FromRgb(20, 88, 138));
        var newBrush = new SolidColorBrush(Color.FromRgb(151, 69, 0));
        var changedBrush = new SolidColorBrush(Color.FromArgb(45, 229, 160, 39));
        var gridPen = new Pen(new SolidColorBrush(Color.FromRgb(217, 226, 236)), 1);
        var axisPen = new Pen(new SolidColorBrush(Color.FromRgb(90, 109, 126)), 1);
        Text("Результат порівняння: 0 / 1", 0, 0, 13);
        foreach (var tick in new[] { 0, 64, 128, 192, 255 })
        {
            var x = X(tick);
            drawingContext.DrawLine(gridPen, new Point(x, area.Top), new Point(x, area.Bottom));
            Text(tick.ToString(CultureInfo.InvariantCulture), x - (tick == 255 ? 20 : 5), area.Bottom + 7, 12);
        }
        drawingContext.DrawLine(gridPen, new Point(area.Left, area.Top), new Point(area.Right, area.Top));
        drawingContext.DrawLine(axisPen, new Point(area.Left, area.Bottom), new Point(area.Right, area.Bottom));
        drawingContext.DrawLine(axisPen, new Point(area.Left, area.Top), new Point(area.Left, area.Bottom));
        Text("1", 23, area.Top - 8, 12);
        Text("0", 23, area.Bottom - 8, 12);
        Text("Внутрішній код, 0–255", area.Left, area.Bottom + 30, 13);

        var rows = Rows;
        if (rows is null || rows.Count == 0)
        {
            Text("Оберіть слот для перегляду моделі.", area.Left + 12, area.Top + 24, 14);
            return;
        }
        foreach (var row in rows.Where(row => row.Before != row.After))
        {
            var left = Math.Max(area.Left, X(row.CompactCode) - area.Width / 510);
            var right = Math.Min(area.Right, X(row.CompactCode) + area.Width / 510);
            drawingContext.DrawRectangle(changedBrush, null, new Rect(left, area.Top, right - left, area.Height));
        }
        // Horizontal then vertical segments: no interpolation or smoothing of
        // boolean outcomes. Both curves remain visible where they coincide.
        DrawSteps(rows, row => row.Before, new Pen(oldBrush, 4));
        DrawSteps(rows, row => row.After, new Pen(newBrush, 2) { DashStyle = DashStyles.Dash });
        drawingContext.DrawLine(new Pen(oldBrush, 4), new Point(area.Left, 34), new Point(area.Left + 24, 34));
        Text("Стара", area.Left + 32, 24, 12);
        drawingContext.DrawLine(new Pen(newBrush, 2) { DashStyle = DashStyles.Dash },
            new Point(area.Left + 110, 34), new Point(area.Left + 134, 34));
        Text("Нова", area.Left + 142, 24, 12);
        Text("Змінені коди — жовте тло", area.Left + 218, 24, 12);

        double X(int value) => area.Left + value * area.Width / 255;

        void DrawSteps(IReadOnlyList<P28PredicateRow> values, Func<P28PredicateRow, bool> state, Pen pen)
        {
            var geometry = new StreamGeometry();
            using (var context = geometry.Open())
            {
                var first = values[0];
                var previousY = state(first) ? area.Top : area.Bottom;
                context.BeginFigure(new Point(X(first.CompactCode), previousY), false, false);
                foreach (var row in values.Skip(1))
                {
                    var x = X(row.CompactCode);
                    var y = state(row) ? area.Top : area.Bottom;
                    context.LineTo(new Point(x, previousY), true, false);
                    context.LineTo(new Point(x, y), true, false);
                    previousY = y;
                }
            }
            geometry.Freeze();
            drawingContext.DrawGeometry(null, pen, geometry);
        }

        void Text(string text, double x, double y, double size)
        {
            var formatted = new FormattedText(text, CultureInfo.GetCultureInfo("uk-UA"),
                FlowDirection.LeftToRight, new Typeface("Segoe UI"), size,
                new SolidColorBrush(Color.FromRgb(52, 73, 92)), VisualTreeHelper.GetDpi(this).PixelsPerDip)
            {
                MaxTextWidth = Math.Max(20, ActualWidth - x),
                Trimming = TextTrimming.CharacterEllipsis,
            };
            drawingContext.DrawText(formatted, new Point(x, y));
        }
    }

    private sealed class PlotAutomationPeer(PredicatePlot owner) : FrameworkElementAutomationPeer(owner)
    {
        protected override string GetClassNameCore() => nameof(PredicatePlot);
        protected override AutomationControlType GetAutomationControlTypeCore() => AutomationControlType.Image;
        protected override string GetHelpTextCore() =>
            "Ступінчасті криві з рядків Core-моделі. Стара — синя, нова — коричнева пунктирна. Жовте тло позначає змінені коди. Не фізичне ввімкнення VTEC.";
    }
}
