using System.Windows;
using System.Windows.Controls;
using System.Windows.Data;
using System.Windows.Media;
using HondaEcu.Desktop.ViewModels;

namespace HondaEcu.Desktop.Controls;

public partial class UnifiedCalibrationPanel : UserControl
{
    public UnifiedCalibrationPanel()
    {
        InitializeComponent();
        MapGrid.Columns.Add(new DataGridTextColumn { Header = "row", Binding = new Binding(nameof(UnifiedMapRow.Index)), IsReadOnly = true, Width = 50 });
        MapGrid.Columns.Add(new DataGridTextColumn { Header = "raw RPM axis", Binding = new Binding(nameof(UnifiedMapRow.Axis)), IsReadOnly = true, Width = 190 });
        for (var col = 0; col < 10; col++)
        {
            var content = new FrameworkElementFactory(typeof(StackPanel));
            content.SetValue(StackPanel.OrientationProperty, Orientation.Vertical);
            var original = new FrameworkElementFactory(typeof(TextBlock));
            original.SetBinding(TextBlock.TextProperty, new Binding($"Cells[{col}].Original") { StringFormat = "original {0}" });
            original.SetValue(TextBlock.FontSizeProperty, 10.0);
            original.SetValue(TextBlock.ForegroundProperty, Brushes.DimGray);
            content.AppendChild(original);
            var requested = new FrameworkElementFactory(typeof(TextBox));
            requested.SetBinding(TextBox.TextProperty, new Binding($"Cells[{col}].Text")
            {
                Mode = BindingMode.TwoWay,
                UpdateSourceTrigger = UpdateSourceTrigger.LostFocus,
                ValidatesOnDataErrors = true,
                NotifyOnValidationError = true
            });
            requested.SetBinding(TextBox.ToolTipProperty, new Binding($"Cells[{col}].Detail"));
            content.AppendChild(requested);
            var column = new DataGridTemplateColumn
            {
                Header = $"c{col}",
                CellTemplate = new DataTemplate { VisualTree = content },
                Width = 83,
                MinWidth = 76
            };
            var style = new Style(typeof(DataGridCell));
            style.Setters.Add(new Setter(BackgroundProperty, new Binding($"Cells[{col}].HeatBrush")));
            style.Setters.Add(new Setter(ToolTipProperty, new Binding($"Cells[{col}].Detail")));
            column.CellStyle = style;
            MapGrid.Columns.Add(column);
        }
        DataContextChanged += (_, args) =>
        {
            if (args.OldValue is UnifiedCalibrationViewModel old) old.CommitEdits = null;
            if (args.NewValue is UnifiedCalibrationViewModel current) current.CommitEdits = CommitDraftEdits;
        };
    }
    private void MapGrid_SelectedCellsChanged(object sender, SelectedCellsChangedEventArgs e)
    {
        if (DataContext is not UnifiedCalibrationViewModel vm) return;
        var selected = MapGrid.SelectedCells.Select(info => (Row: (info.Item as UnifiedMapRow)?.Index ?? -1,
            Column: info.Column.DisplayIndex - 2)).Where(cell => cell.Row is >= 0 and < 20 && cell.Column is >= 0 and < 10).ToArray();
        if (selected.Length == 0) return;
        var top = selected.Min(cell => cell.Row); var bottom = selected.Max(cell => cell.Row);
        var left = selected.Min(cell => cell.Column); var right = selected.Max(cell => cell.Column);
        if (selected.Length == (bottom - top + 1) * (right - left + 1)) vm.SelectRectangle(top, left, bottom, right);
        else vm.RejectNonRectangularSelection();
    }
    public bool CommitDraftEdits()
    {
        foreach (var text in Descendants<TextBox>(MapGrid)) text.GetBindingExpression(TextBox.TextProperty)?.UpdateSource();
        var committed = MapGrid.CommitEdit(DataGridEditingUnit.Cell, true) && MapGrid.CommitEdit(DataGridEditingUnit.Row, true);
        if (DataContext is UnifiedCalibrationViewModel vm && !vm.SelectedMap.Included) return true;
        return committed && !Descendants<DependencyObject>(MapGrid).Any(Validation.GetHasError);
    }
    private static IEnumerable<T> Descendants<T>(DependencyObject parent) where T : DependencyObject
    {
        for (var i = 0; i < VisualTreeHelper.GetChildrenCount(parent); i++)
        {
            var child = VisualTreeHelper.GetChild(parent, i);
            if (child is T typed) yield return typed;
            foreach (var nested in Descendants<T>(child)) yield return nested;
        }
    }
}
