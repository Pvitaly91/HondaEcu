using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using HondaEcu.Desktop.ViewModels;

namespace HondaEcu.Desktop.Controls;

public partial class BasicCalibrationPanel : UserControl
{
    public BasicCalibrationPanel()
    {
        InitializeComponent();
        DataContextChanged += (_, args) =>
        {
            if (args.OldValue is BasicCalibrationViewModel old) old.CommitEdits = null;
            if (args.NewValue is BasicCalibrationViewModel current) current.CommitEdits = CommitDraftEdits;
        };
    }
    public bool CommitDraftEdits()
    {
        // Commit the active binding/cell/row without focus, input or desktop automation.
        foreach (var grid in Descendants<DataGrid>(Groups))
        {
            if (!grid.IsEnabled) continue;
            foreach (var text in Descendants<TextBox>(grid)) text.GetBindingExpression(TextBox.TextProperty)?.UpdateSource();
            if (!grid.CommitEdit(DataGridEditingUnit.Cell, true) || !grid.CommitEdit(DataGridEditingUnit.Row, true) ||
                Descendants<DependencyObject>(grid).Any(Validation.GetHasError)) return false;
        }
        return true;
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
