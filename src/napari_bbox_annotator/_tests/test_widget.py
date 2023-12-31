import numpy as np

from napari_bbox_annotator import BboxAnnotatorWidget


# make_napari_viewer is a pytest fixture that returns a napari viewer object
# capsys is a pytest fixture that captures stdout and stderr output streams
def test_widget(make_napari_viewer):
    # make viewer and add an image layer using our fixture
    viewer = make_napari_viewer()
    viewer.add_image(np.random.random((100, 100)))

    # create our widget, passing in the viewer
    my_widget = BboxAnnotatorWidget(viewer)

def test_annotation(make_napari_viewer):
    import os
    from pathlib import Path

    dummy_boxes = [np.array([
            [80, 51],
            [80, 73],
            [93, 73],
            [93, 51]
        ], dtype=float),
        np.array([
            [72, 61],
            [72, 74],
            [85, 74],
            [85, 61]
        ], dtype=float)]

    viewer = make_napari_viewer()

    # create our widget, passing in the viewer
    my_widget = BboxAnnotatorWidget(viewer)
    viewer.window.add_dock_widget(my_widget)

    # add row to tableWidget_annotations
    my_widget._on_add_row()
    my_widget._on_add_row()

    # get location of current file
    current = Path(__file__).parent.absolute()

    my_widget._directory_path = os.path.join(current, 'imgs')
    my_widget._label_dir = os.path.join(current, 'labels')
    os.makedirs(my_widget._label_dir, exist_ok=True)
    for file in os.listdir(my_widget._directory_path):
        my_widget.listWidget_files.addItem(file)

    # select first item
    my_widget.listWidget_files.setCurrentRow(0)

    viewer.layers['Cell_boxes'].data = dummy_boxes
    my_widget._on_next_image()

    viewer.layers['Cell_boxes'].data = dummy_boxes
    my_widget._on_next_image()

    assert len(viewer.layers['Cell_boxes'].data) == 0
    assert len(viewer.layers['2_boxes'].data) == 0
    assert len(viewer.layers['3_boxes'].data) == 0

    # select first item again
    my_widget.listWidget_files.setCurrentRow(0)

    # make sure boxes are still there
    for i, box in enumerate(viewer.layers['Cell_boxes'].data):
        assert np.allclose(box, dummy_boxes[i], atol=1e-5)
