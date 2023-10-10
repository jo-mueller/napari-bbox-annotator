"""
This module is an example of a barebones QWidget plugin for napari

It implements the Widget specification.
see: https://napari.org/stable/plugins/guides.html?#widgets

Replace code below according to your needs.
"""
from typing import TYPE_CHECKING

import os
from pathlib import Path
import pandas as pd

from magicgui import magic_factory
from qtpy.QtWidgets import QTableWidgetItem, QWidget, QFileDialog
from qtpy import uic
from qtpy.QtGui import QColor

if TYPE_CHECKING:
    import napari


class YoloAnnotatorWidget(QWidget):
    def __init__(self, napari_viewer: "napari.Viewer"):
        super().__init__()
        self.napari_viewer = napari_viewer

        self._image_layer = None
        self._box_labels = None

        # set some nice colors for the classes
        self._edge_colors = [
            'orange',
            'blue',
            'green',
            'yellow',
        ]

        # load layout from ui file
        uic.loadUi(os.path.join(Path(__file__).parent, "./annotator.ui"), self)

        # connect functions to buttons
        self.pushButton_browse.clicked.connect(self._on_browse_button_clicked)
        self.listWidget_files.itemSelectionChanged.connect(self._on_image_list_selected)
        self.pushButton_add_class.clicked.connect(self._on_add_row)
        self.tableWidget_annotations.itemSelectionChanged.connect(self._on_select_class)
        self.pushButton_next.clicked.connect(self._on_next_image)

        # select first row in tableWidget_annotations
        self.tableWidget_annotations.setCurrentCell(0, 0)

    def _on_next_image(self):

        # save all bounding boxes to csv file
        annotations = pd.DataFrame(columns=['class', 'x', 'y', 'width', 'height'])
        for i in range(self.tableWidget_annotations.rowCount()):
            name_layer = self.tableWidget_annotations.item(i, 0).text() + "_boxes"
            boxes = self.napari_viewer.layers[name_layer].data

            image_dim1 = self._image_layer.data.shape[0]
            image_dim2 = self._image_layer.data.shape[1]

            for box in boxes:
                center = box.mean(axis=0)
                # add as row to dataframe without append
                annotations.loc[len(annotations)] = [
                    int(i),
                    center[0] / image_dim1,
                    center[1] / image_dim2,
                    abs(box[1, 1] - box[1, 0]) / image_dim1,
                    abs(box[-1, 0] - box[0, 0]) / image_dim2]

        os.makedirs(self._label_dir, exist_ok=True)
        item = self.listWidget_files.selectedItems()[0]
        annotations.to_csv(os.path.join(self._label_dir, item.text().replace('.png', '.txt')),
                           index=False, header=False, sep=' ')

        # make current text color green
        self.listWidget_files.currentItem().setForeground(QColor('green'))

        # Move to next item
        index = self.listWidget_files.currentRow()
        self.listWidget_files.setCurrentRow(index+1)

    def _on_browse_button_clicked(self):
        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.Directory)
        file_dialog.setOption(QFileDialog.ShowDirsOnly, True)
        # set default directory to current directory
        file_dialog.setDirectory(r'C:\Users\johamuel\Nextcloud\Shared\BiAPoL\projects\121_organoids_in_microwell_plates\yolo_training\dataset\images')
        file_dialog.exec_()
        self._directory_path = file_dialog.selectedFiles()[0]
        self.lineEdit_directory.setText(self._directory_path)

        # find all files in directory and add to listWidget_files
        self.listWidget_files.clear()
        for file in os.listdir(self._directory_path):
            self.listWidget_files.addItem(file)

        self._label_dir = os.path.join(self._directory_path, '..', 'labels')

    def _on_image_list_selected(self):
        from skimage import io

        # get selected item
        item = self.listWidget_files.selectedItems()[0]

        # clear previous image
        if self._image_layer is not None:
            self.napari_viewer.layers.remove(self._image_layer.name)

        # clear previous boxes
        for layer in self.napari_viewer.layers:
            if layer.name.endswith('_boxes'):
                self.napari_viewer.layers.remove(layer.name)

        # load image from listWidget_files
        self._image_path = os.path.join(self._directory_path, item.text())
        image = io.imread(self._image_path)
        self._image_layer = self.napari_viewer.add_image(image, name=item.text(),
                                                         blending='additive')

        # create shapes layers
        self._update_shapes_layers()

    def _update_shapes_layers(self):

        if len(self.napari_viewer.layers) == 0:
            return

        # create empty shapes layer in viewer for every class
        for i in range(self.tableWidget_annotations.rowCount()):
            name = self.tableWidget_annotations.item(i, 0).text() + "_boxes"
            if name not in self.napari_viewer.layers:
                color = self._edge_colors[i]
                self.napari_viewer.add_shapes(
                    name=name,
                    shape_type='rectangle',
                    edge_width=1,
                    edge_color=color,
                    opacity=0.5)

        self._on_select_class()

    def _on_add_row(self):
        # put next higher number in first column
        row_count = self.tableWidget_annotations.rowCount()
        self.tableWidget_annotations.insertRow(row_count)

        self.tableWidget_annotations.setItem(
            row_count, 0, QTableWidgetItem(str(row_count+1)))

        self._update_shapes_layers()

    def _on_select_class(self):

        if self._image_layer is None:
            return

        row = self.tableWidget_annotations.currentRow()
        item = self.tableWidget_annotations.item(row, 0).text()
        name_layer = item + "_boxes"

        active_layer = self.napari_viewer.layers[name_layer]
        self.napari_viewer.layers.selection.active = active_layer
        active_layer.mode = 'add_rectangle'
