"""Template Explorer — organise the saved-object (template) library.

A tree view of the objects folder: create sub-folders, rename, move,
delete and insert saved objects. The left toolbar's Objects dropdown
mirrors the same folder structure as nested sub-menus.

Copyright (C) 2026 Gwilherm Kerherve

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.
"""

from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QDialog, QHBoxLayout, QInputDialog, QLabel,
                             QMessageBox, QPushButton, QTreeWidget,
                             QTreeWidgetItem, QVBoxLayout)

from . import icons, library


class TemplateExplorer(QDialog):
    """Manage the object/template library; insert objects onto the canvas."""

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.setWindowTitle("Template Explorer")
        self.setMinimumSize(440, 480)
        layout = QVBoxLayout(self)

        info = QLabel("Organise your saved objects into folders. "
                      "Double-click an object to insert it on the canvas.")
        info.setWordWrap(True)
        layout.addWidget(info)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemDoubleClicked.connect(self._on_double_click)
        layout.addWidget(self.tree, 1)

        row = QHBoxLayout()
        for label, slot in (("New folder", self._new_folder),
                            ("Rename", self._rename),
                            ("Move to…", self._move),
                            ("Delete", self._delete),
                            ("Insert", self._insert)):
            btn = QPushButton(label)
            btn.clicked.connect(slot)
            row.addWidget(btn)
        layout.addLayout(row)

        bottom = QHBoxLayout()
        open_btn = QPushButton("Open folder on disk")
        open_btn.clicked.connect(self.window.open_objects_folder)
        bottom.addWidget(open_btn)
        bottom.addStretch(1)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        bottom.addWidget(close)
        layout.addLayout(bottom)

        self._reload()

    # ------------------------------------------------------------ tree
    def _reload(self):
        self.tree.clear()
        self._folders = {(): None}            # rel-parts -> item (None=root)
        for parts in library.list_folders():
            parent = self._folders.get(tuple(parts[:-1]))
            item = QTreeWidgetItem([parts[-1]])
            item.setData(0, Qt.UserRole, ("folder", tuple(parts)))
            item.setIcon(0, icons.icon("mdi.folder-outline"))
            self._add(parent, item)
            self._folders[tuple(parts)] = item
        for parts, name, path in library.iter_objects():
            item = QTreeWidgetItem([name])
            item.setData(0, Qt.UserRole, ("object", str(path)))
            item.setIcon(0, icons.icon("mdi.shape-outline"))
            self._add(self._folders.get(tuple(parts)), item)
        self.tree.expandAll()

    def _add(self, parent, item):
        (parent.addChild if parent else self.tree.addTopLevelItem)(item)

    def _selected(self):
        items = self.tree.selectedItems()
        return items[0].data(0, Qt.UserRole) if items else None

    def _target_folder(self):
        """Folder to act in: the selected folder, or the one holding the
        selected object, else the root."""
        sel = self._selected()
        if sel is None:
            return ()
        if sel[0] == "folder":
            return sel[1]
        rel = Path(sel[1]).parent.relative_to(library.objects_dir())
        return () if str(rel) == "." else rel.parts

    # ------------------------------------------------------------ actions
    def _new_folder(self):
        name, ok = QInputDialog.getText(self, "New folder", "Folder name:")
        if ok and name.strip():
            library.create_folder(tuple(self._target_folder()) + (name,))
            self._reload()

    def _rename(self):
        sel = self._selected()
        if sel is None:
            return
        kind, payload = sel
        old = payload[-1] if kind == "folder" else Path(payload).stem
        name, ok = QInputDialog.getText(self, "Rename", "New name:", text=old)
        if not (ok and name.strip()):
            return
        if kind == "object":
            library.rename_object(payload, name)
        else:
            library.rename_folder(payload, name)
        self._reload()

    def _move(self):
        sel = self._selected()
        if sel is None or sel[0] != "object":
            QMessageBox.information(self, "Move", "Select an object to move.")
            return
        choices = ["(top level)"] + ["/".join(p) for p in library.list_folders()]
        dest, ok = QInputDialog.getItem(self, "Move to", "Destination folder:",
                                        choices, 0, False)
        if ok:
            library.move_object(sel[1], () if dest == "(top level)" else dest)
            self._reload()

    def _delete(self):
        sel = self._selected()
        if sel is None:
            return
        kind, payload = sel
        what = "folder and everything in it" if kind == "folder" else "object"
        if QMessageBox.question(
                self, "Delete", f"Delete this {what}?") != QMessageBox.Yes:
            return
        if kind == "object":
            library.delete_object(payload)
        else:
            library.delete_folder(payload)
        self._reload()

    def _insert(self):
        sel = self._selected()
        if sel and sel[0] == "object":
            self.window.insert_object(sel[1])
            self.accept()

    def _on_double_click(self, item, _column):
        data = item.data(0, Qt.UserRole)
        if data and data[0] == "object":
            self.window.insert_object(data[1])
            self.accept()
