# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2023 Adrian Przekwas <adrian.v.przekwas@gmail.com>

# This simple script creates or updates labels in the 3D view, based on sensor's Label2

import FreeCAD as App
sensor_label = 'sensor'

def aul():
    doc = App.ActiveDocument
    labels = []
    sensors = doc.findObjects(Label=sensor_label)
    for idx,s in enumerate(sensors):
        if not doc.getObject('chlabel'+str(idx)):
            doc.addObject("App::AnnotationLabel", 'chlabel'+str(idx))

        label = doc.getObject('chlabel'+str(idx))
        label.ViewObject.BackgroundColor = (1.00,0.00,0.00)
        label.LabelText = 'ch' + s.Label2
        label.BasePosition = s.LinkPlacement.Base
        labels.append(label)

    if not doc.getObject('LGroup'):
        doc.addObject("App::DocumentObjectGroup","LGroup")

    gr = doc.getObject('LGroup')
    gr.Label="Label Group"
    gr.addObjects(labels)

if __name__ == '__main__':
    aul()
