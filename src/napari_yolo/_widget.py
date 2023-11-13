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

    def _check_existing_anntations(self):
        # check if there are already annotations for the selected image
        for i in range(self.listWidget_files.count()):
            item = self.listWidget_files.item(i)
            if os.path.exists(os.path.join(self._label_dir, item.text().replace('.png', '.txt'))):
                item.setForeground(QColor('green'))

    def _on_next_image(self):

        # save all bounding boxes to csv file
        annotations = pd.DataFrame(columns=['class', 'x', 'y', 'width', 'height'])
        os.makedirs(self._label_dir, exist_ok=True)

        for i in range(self.tableWidget_annotations.rowCount()):
            name_layer = self.tableWidget_annotations.item(i, 0).text() + "_boxes"
            boxes = self.napari_viewer.layers[name_layer].data

            image_dim1 = self._image_layer.data.shape[0]
            image_dim2 = self._image_layer.data.shape[1]

            for box in boxes:
                x = box[:, 0]
                y = box[:, 1]
                width = x.max() - x.min()
                height = y.max() - y.min()
                center_x = x.mean()
                center_y = y.mean()
                # add as row to dataframe without append
                annotations.loc[len(annotations)] = [
                    int(i),
                    center_x / image_dim1,
                    center_y / image_dim2,
                    width / image_dim1,
                    height / image_dim2
                    ]

        item = self.listWidget_files.selectedItems()[0]
        annotations.to_csv(os.path.join(self._label_dir, item.text().replace('.png', '.txt')),
                           index=False, header=False, sep=' ')

        # make current text color green
        self.listWidget_files.currentItem().setForeground(QColor('green'))

        # Move to next item
        index = self.listWidget_files.currentRow()
        if index < self.listWidget_files.count() - 1:
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

        # if no folder was selected
        if self._directory_path == '':
            return

        # find all files in directory and add to listWidget_files
        self.listWidget_files.clear()
        for file in os.listdir(self._directory_path):
            self.listWidget_files.addItem(file)

        self._label_dir = os.path.join(self._directory_path, '..', 'labels')
        self._check_existing_anntations()

    def _on_image_list_selected(self):
        from skimage import io

        # get selected item
        item = self.listWidget_files.selectedItems()[0]

        # clear previous image
        if self._image_layer is not None:
            self.napari_viewer.layers.remove(self._image_layer.name)

        # clear previous boxes
        layers_to_remove = [layer.name for layer in self.napari_viewer.layers if layer.name.endswith('_boxes')]
        for name in layers_to_remove:
            self.napari_viewer.layers.remove(name)

        # load image from listWidget_files
        self._image_path = os.path.join(self._directory_path, item.text())
        image = io.imread(self._image_path)
        self._image_layer = self.napari_viewer.add_image(image, name=item.text(),
                                                         blending='additive')
        
        # create shapes layers
        self._update_shapes_layers()
        
        # load annotations if they exist
        label_file = os.path.join(self._label_dir, item.text().replace('.png', '.txt'))

        if os.path.exists(label_file):
            classes, vertices = self._load_annotations(label_file)
            if classes is None:
                return
            for obj_class, box in zip(classes, vertices):
                # get name from tableWidget_annotations
                name = self.tableWidget_annotations.item(int(obj_class), 0).text() + "_boxes"
                self.napari_viewer.layers[name].add(
                    box, shape_type='rectangle')

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

    def _load_annotations(self, filename):
        import numpy as np
        try:
            self._box_labels = pd.read_csv(filename, header=None, sep=' ')
        except Exception:
            return None, None
        self._box_labels.columns = ['class', 'x', 'y', 'width', 'height']
        self._box_labels['x'] = self._box_labels['x'] * self._image_layer.data.shape[0]
        self._box_labels['y'] = self._box_labels['y'] * self._image_layer.data.shape[1]
        self._box_labels['width'] = self._box_labels['width'] * self._image_layer.data.shape[0]
        self._box_labels['height'] = self._box_labels['height'] * self._image_layer.data.shape[1]

        boxes = []
        classes = []
        for i in range(self._box_labels.shape[0]):
            x, y, w, h = self._box_labels.iloc[i, 1:].values
            vertices = self._bbox_to_vertices(x, y, w, h)
            boxes.append(vertices)
            classes.append(self._box_labels.iloc[i, 0])

        return classes, np.array(boxes)


    # def correct_messy_annotations(self, h, _w, x1, x2):
    #     import numpy as np
    #     A =  np.array([
    #         [1, -1, 0, 0],
    #         [0.5, 0.5, 0, 0],
    #         [0, 0, 0.5, 0.5],
    #         [0, 1, 0, -1]
    #     ])

    #     b = np.array([h, x1, x2, _w])

    #     ymax, ymin, xmax, xmin = np.linalg.solve(A, b)

    #     correct_width = xmax - xmin
    #     correct_height = ymax - ymin

    #     vertices = np.array([
    #         [ymin, xmin],
    #         [ymin, xmax],
    #         [ymax, xmax],
    #         [ymax, xmin]
    #     ])

    #     # if eccentricity is too high, then the annotation is probably wrong
    #     long_side = max(correct_width, correct_height)
    #     short_side = min(correct_width, correct_height)
    #     eccentricity = abs(long_side / short_side)
    #     if eccentricity < 1.5:
    #         return vertices
    #     else: 
    #         return self.correct_messy_annotations(h, -_w, x1, x2)


    def _bbox_to_vertices(self, x_center, y_center, width, height):
        x_min = x_center - width / 2
        x_max = x_center + width / 2
        y_min = y_center - height / 2
        y_max = y_center + height / 2

        return [
            [x_min, y_min],
            [x_min, y_max],
            [x_max, y_max],
            [x_max, y_min],
        ]
        
    
    def _vertices_to_bbox(self, vertices):
        center_x = vertices[:, 0].mean()
        center_y = vertices[:, 1].mean()
        width = vertices[:, 0].max() - vertices[:, 0].min()
        height = vertices[:, 1].max() - vertices[:, 1].min()

        return center_x, center_y, width, height
