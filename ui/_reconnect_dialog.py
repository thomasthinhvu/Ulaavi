"""
Preview dialog for Reconnect missing media.

Lists every planned path change with a checkbox, so the user can untick the wrong ones
before anything is written to data.json.
"""
try:
    from PySide2 import QtWidgets, QtCore
except ModuleNotFoundError:
    from PySide6 import QtWidgets, QtCore


class ReconnectDialog(QtWidgets.QDialog):
    """Show planned changes and return the ones the user kept."""

    def __init__(self, plan: dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Reconnect missing media - preview')
        self.resize(900, 500)

        self._changes = plan.get('changes', [])
        stats = plan.get('stats', {})

        layout = QtWidgets.QVBoxLayout(self)

        summary = (f"{len(self._changes)} change(s) planned. "
                   f"Still missing: {len(stats.get('missing', []))}, "
                   f"ambiguous (not changed): {len(stats.get('ambiguous', []))}.")
        layout.addWidget(QtWidgets.QLabel(summary))

        self._table = QtWidgets.QTableWidget(len(self._changes), 4, self)
        self._table.setHorizontalHeaderLabels(['Apply', 'Field', 'Old path', 'New path'])
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        for row, change in enumerate(self._changes):
            check = QtWidgets.QTableWidgetItem()
            check.setFlags(QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled)
            check.setCheckState(QtCore.Qt.Checked)
            self._table.setItem(row, 0, check)
            self._table.setItem(row, 1, QtWidgets.QTableWidgetItem(change['field']))
            self._table.setItem(row, 2, QtWidgets.QTableWidgetItem(change['old']))
            self._table.setItem(row, 3, QtWidgets.QTableWidgetItem(change['new']))

        layout.addWidget(self._table)

        row_buttons = QtWidgets.QHBoxLayout()
        select_all = QtWidgets.QPushButton('Select all', self)
        select_none = QtWidgets.QPushButton('Select none', self)
        select_all.clicked.connect(lambda: self._set_all(QtCore.Qt.Checked))
        select_none.clicked.connect(lambda: self._set_all(QtCore.Qt.Unchecked))
        row_buttons.addWidget(select_all)
        row_buttons.addWidget(select_none)
        row_buttons.addStretch()
        layout.addLayout(row_buttons)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _set_all(self, state) -> None:
        """Check or uncheck every row."""
        for row in range(self._table.rowCount()):
            self._table.item(row, 0).setCheckState(state)

    def selected_changes(self) -> list:
        """Return the changes whose checkbox is ticked."""
        return [change for row, change in enumerate(self._changes)
                if self._table.item(row, 0).checkState() == QtCore.Qt.Checked]
