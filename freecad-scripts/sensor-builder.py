# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2023 Adrian Przekwas <adrian.v.przekwas@gmail.com>

# This script helps with placing sensors on a tracker shape, also prepares places for sensor mounting.
# It expect a shape object with label "tracker-base" and sensors models imported as links with labels containing "sensor" string (eg. sensor1, sensor2...)
# Also requires link to a tracker mainboard model, with label "tracker-mainboard".
# For preparing sensor mounting places and/or photodiode apertures, there is a single link "stamp" needed. "stamp" stape will be used for cutting material from "tracker-base"
# Optional "stamp-simplified" should be a simple shape for creating apertures - useful for creating simple version for simulation.
# "sensor" should have to two LCS-es (local coordinate system): "LCS-Base" (for placing on the 'tracker-base' surface) and "LCS-Diode" (used in sensor-extraction.py)
# "stamp" and "stamp-simplified" need "LCS-Base" that will be aligned with a sensor one. "tracker-mainboard" needs "LCS_IMU" for IMU (inertial measurement unit) placement

# Basic workflow:
# Create a Part Design Body representing sensor support shape, set "tracker-base" label
# Import sensor as link (App::Link), repeat for next sensors - in the tree, you should see "sensor", "sensor001", "sensor002"...
# Import (as link) "stamp" single time
# Import (as link) "tracker-mainboard"
# Place sensors near to "tracker-base" surface
# Run place_cut_sensors() - it will find closest point on the support shape surface for every sensor, move sensors and prepare support places
# You can do a manual adjustment of a sensor placement, after this use recut_sensors() to recreate support places
# You can save (in a spreadsheet object) adjustments values with save_corr() and load them with load_corr()
# place_cut_sensors(True) and recut_sensors(True) uses "stamp-simplified" for cutting shape

import FreeCAD as App
import FreeCADGui as Gui
import Part
import math

doc = App.ActiveDocument
sensor_label = 'sensor'
stamp_label = 'stamp'
stamp_simple_label = 'stamp-simplified'
tracker_base_label = 'tracker-base'
mainboard_label = 'tracker-mainboard'

initial_dir = App.Vector(-1, 0, 0) # sets initial orientation of sensors,
                                   # later modified by mainboard orientation

Gui.activateWorkbench('PartDesignWorkbench')
Gui.ActiveDocument.ActiveView.setActiveObject('pdbody',doc.getObjectsByLabel(tracker_base_label)[0])

def add_vertex(vec, name):
    if doc.getObject(name) == None:
        doc.getObjectsByLabel(tracker_base_label)[0].newObject('PartDesign::Point', name)

    vtx = doc.getObject(name)
    vtx.Placement=App.Placement(App.Vector(vec.x,vec.y,vec.z),App.Rotation(App.Vector(0.00,0.00,1.00),0.00))
    return vtx

def add_attach_lcs(pvtx, nvtx, avtx, name):
    if doc.getObject(name) == None:
        doc.getObjectsByLabel(tracker_base_label)[0].newObject('PartDesign::CoordinateSystem', name)

    lcs = doc.getObject(name)
    lcs.Support = [(pvtx,''),(nvtx,''),(avtx,'')]
    lcs.MapMode = 'OZX'
    doc.recompute()
    return lcs

def find_point_normal(shape, pos):
    vertex = Part.Vertex(pos)
    #Part.show(vertex)
    for solid in shape.Solids:
        if solid.isValid():
            min_distance = 10000.0
            last_point_on_face = App.Vector(0.0, 0.0, 0.0)
            last_normal = App.Vector(0.0, 0.0, 0.0)
            for face in solid.Faces:
                distance, point_on_face, info = vertex.distToShape(face) #Returns: float<minimum distance>,list<nearest points>,list<nearest subshapes & parameters>
                surf = face.Surface
                u, v = surf.parameter(point_on_face[0][1]) #why [0][1]? https://github.com/FreeCAD/FreeCAD-documentation/blob/main/wiki/TopoShape_API.md
                normal = face.normalAt(u, v)
                #print (face, point, point_on_face, "Distance = ", distance)
                #print (point_on_face[0][0], "uv = ", u, v, "Normal= ", normal, "Distance = ", distance)
                if (distance < min_distance):
                    min_distance = distance
                    last_point_on_face = point_on_face[0][1]
                    last_normal = normal

            return last_point_on_face, last_normal

def find_pl(s):
    try:
        link_pl = s.LinkPlacement
        s_doc = s.getLinkedObject().Document
        lcsbase_pl = s_doc.getObjectsByLabel('LCS-Base')[0].Placement
    except:
        print("No LCS-Base found, aborting")
        return None, None
    return link_pl, lcsbase_pl

def find_mainboard_imu_pl():
    try:
        mb = doc.getObjectsByLabel(mainboard_label)[0]
        link_pl = mb.LinkPlacement
        mb_doc = mb.getLinkedObject().Document
        lcsimu_pl = mb_doc.getObjectsByLabel('LCS-IMU')[0].Placement
    except:
        print("No LCS-IMU found, aborting")
        return None, None
    return link_pl, lcsimu_pl

def create_lcses_sensors (sensors, tracker_shape):
    mb_link_pl, _ = find_mainboard_imu_pl()
    dir = mb_link_pl.Rotation * initial_dir
    lcses = []
    for idx, s in enumerate(sensors):
        link_pl, lcsbase_pl = find_pl(s)
        total_pl = link_pl * lcsbase_pl
        print (total_pl)
        position = total_pl.Base
        point, normal = find_point_normal(tracker_shape, position)
        print (point, normal)
        pvtx = add_vertex(point, 'p_surf' + str (idx))
        nvtx = add_vertex((point + normal), 'p_norm' + str (idx))
        avtx = add_vertex((point + dir), 'p_aux' + str (idx))
        lcs = add_attach_lcs(pvtx, nvtx, avtx, 's_lcs' + str (idx))
        lcses.append(lcs)
    return lcses

def move_to_lcses(lcses, sensors):
    for idx, lcs in enumerate(lcses):
        s = sensors[idx]
        lcs_pl = lcs.Placement
        link_pl, lcsbase_pl = find_pl(s)
        pl = lcs_pl * lcsbase_pl.inverse()
        s.LinkPlacement = pl
        doc.recompute()

def move_to_corrected_lcses(lcses, sensors, pl_diffs):
    for idx, lcs in enumerate(lcses):
        s = sensors[idx]
        pl_ds = pl_diffs[idx]
        lcs_pl =  lcs.Placement
        link_pl, lcsbase_pl = find_pl(s)
        lcs_corr = lcs_pl * pl_ds
        pl = lcs_corr * lcsbase_pl.inverse()
        s.LinkPlacement = pl
        doc.recompute()

def move_cut_stamps(lcses, stamp, tracker_shape):
    try:
        lo = stamp.getLinkedObject()
        stamp_doc = lo.Document
        lcsbase_pl = stamp_doc.getObjectsByLabel('LCS-Base')[0].Placement
        shape = lo.Shape
        temp_shape = tracker_shape
    except:
        print("No LCS-Bae or valid shape found, aborting")
        return
    for idx, lcs in enumerate(lcses):
        lcs_pl = lcs.Placement
        copied_stamp = shape.copy()
        copied_stamp.Placement = lcs_pl * lcsbase_pl.inverse()
        temp_shape = temp_shape.cut(copied_stamp)
        # Part.show(temp_shape)

    return temp_shape

def find_sensor_lcs_pl_corr(lcses, sensors): # if user corrected the sensor placement by hand after alignment, there will be placement difference beetween sensor and LCS placed on tracker shape
    pl_ds = []
    for idx, lcs in enumerate(lcses):
        s = sensors[idx]
        lcs_pl = lcs.Placement
        link_pl, lcsbase_pl = find_pl(s)
        total_pl = link_pl * lcsbase_pl
        pl_t = lcs_pl.inverse() * total_pl
        print ('Sensor and LCS ' + str(idx) + ' placement difference: ' + str (pl_t))
        pl_ds.append(pl_t)
    return pl_ds

# places sensors (relative to ther base LCS-es) on nearest surface
# then cuts material with stamp model to get flat (or other required shape) surface to mount sensor

def place_cut_sensors(simple = False):
    try:
        tracker_obj = doc.getObjectsByLabel(tracker_base_label)[0]
        tracker_shape = tracker_obj.Shape
    except:
        print("No valid tracker shape found, aborting")
        return
    try:
        if simple:
            stamp = doc.getObjectsByLabel(stamp_simple_label)[0]
        else:
            stamp = doc.getObjectsByLabel(stamp_label)[0]
    except:
        print("No stamp found, aborting")
        return
    sensors = doc.findObjects(Label=sensor_label)
    lcses = create_lcses_sensors(sensors, tracker_shape)
    move_to_lcses(lcses, sensors)

    cut_shape = move_cut_stamps(lcses, stamp, tracker_shape)
    if simple:
        if not doc.getObject('cut_obj_sim'):
            doc.addObject("Part::Feature", 'cut_obj_sim')

        c_objsim = doc.getObject('cut_obj_sim')
        c_objsim.Shape = cut_shape
        c_objsim.Label = 'Tracker edited (simple)'

        tracker_obj.ViewObject.Visibility = False
        c_objsim.ViewObject.Transparency = 50
    else:
        if not doc.getObject('cut_obj'):
            doc.addObject("Part::Feature", 'cut_obj')

        c_obj = doc.getObject('cut_obj')
        c_obj.Shape = cut_shape
        c_obj.Label = 'Tracker edited'

        tracker_obj.ViewObject.Visibility = False
        c_obj.ViewObject.Transparency = 50

# after sensor placement modification by user, new surfaces for placing sensors are needed
def recut_sensors(simple = False):
    try:
        tracker_obj = doc.getObjectsByLabel(tracker_base_label)[0]
        tracker_shape = tracker_obj.Shape
    except:
        print("No valid tracker shape found, aborting")
        return
    try:
        if simple:
            stamp = doc.getObjectsByLabel(stamp_simple_label)[0]
        else:
            stamp = doc.getObjectsByLabel(stamp_label)[0]
    except:
        print("No stamp found, aborting")
        return
    lcses = doc.findObjects(Label='s_lcs')
    sensors = doc.findObjects(Label=sensor_label)

    for idx,s in enumerate(sensors):
        link_pl, lcsbase_pl = find_pl(s)
        total_pl = link_pl * lcsbase_pl
        lcses[idx].Placement = total_pl

    cut_shape = move_cut_stamps(lcses, stamp, tracker_shape)

    if simple:
        if not doc.getObject('cut_obj_sim'):
            doc.addObject("Part::Feature", 'cut_obj_sim')

        c_objsim = doc.getObject('cut_obj_sim')
        c_objsim.Shape = cut_shape
        c_objsim.Label = 'Tracker edited (simple)'

        tracker_obj.ViewObject.Visibility = False
        c_objsim.ViewObject.Transparency = 50
    else:
        if not doc.getObject('cut_obj'):
            doc.addObject("Part::Feature", 'cut_obj')

        c_obj = doc.getObject('cut_obj')
        c_obj.Shape = cut_shape
        c_obj.Label = 'Tracker edited'

        tracker_obj.ViewObject.Visibility = False
        c_obj.ViewObject.Transparency = 50

def write_sensors_spreadsheet(spr, pl_ds):
    for idx, pl in enumerate(pl_ds):
        cell_i = str(idx + 2)
        spr.set('A' + cell_i, str(pl.Base.x))
        spr.set('B' + cell_i, str(pl.Base.y))
        spr.set('C' + cell_i, str(pl.Base.z))
        spr.set('D' + cell_i, str(pl.Rotation.Angle * 180 / math.pi))
        spr.set('E' + cell_i, str(pl.Rotation.Axis.x))
        spr.set('F' + cell_i, str(pl.Rotation.Axis.y))
        spr.set('G' + cell_i, str(pl.Rotation.Axis.z))
        doc.recompute()

def read_sensors_spreadsheet(spr, sens):
    ret_pl = []
    for idx, s in enumerate(sens):
        cell_i = str(idx + 2)
        x = spr.get('A' + cell_i)
        y = spr.get('B' + cell_i)
        z = spr.get('C' + cell_i)
        angle = spr.get('D' + cell_i)
        axis_x = spr.get('E' + cell_i)
        axis_y = spr.get('F' + cell_i)
        axis_z = spr.get('G' + cell_i)
        pl = App.Placement(App.Vector(x, y, z),App.Rotation(App.Vector(axis_x, axis_y, axis_z), angle))
        ret_pl.append(pl)
    return ret_pl

# if user correcter sensor placement by hand, this will save it in a spreadsheet
def save_corr():
    lcses = doc.findObjects(Label='s_lcs')
    sensors = doc.findObjects(Label=sensor_label)
    if not doc.getObject('SensorSpreadsheet'):
        doc.addObject('Spreadsheet::Sheet','SensorSpreadsheet')

    spr_obj = doc.getObject('SensorSpreadsheet')
    spr_obj.set('A1', 'X')
    spr_obj.set('B1', 'Y')
    spr_obj.set('C1', 'Z')
    spr_obj.set('D1', 'angle')
    spr_obj.set('E1', 'axis X')
    spr_obj.set('F1', 'axis Y')
    spr_obj.set('G1', 'axis Z')
    pl_diffs = find_sensor_lcs_pl_corr(lcses, sensors)
    print (pl_diffs)
    write_sensors_spreadsheet(spr_obj, pl_diffs)

# loads drom spreadsheet corrected placement by user
# if tracker shape changed sensor will follow the change and then apply the correction
def load_corr():
    lcses = doc.findObjects(Label='s_lcs')
    sensors = doc.findObjects(Label=sensor_label)
    if not doc.getObject('SensorSpreadsheet'):
        print ('Spreadsheet not found!')
        return
    spr_obj = doc.getObject('SensorSpreadsheet')
    pl_diffs = read_sensors_spreadsheet(spr_obj, sensors)
    if len(lcses) != len(pl_diffs):
        print ('Number of corrected placements and sensors LCS-es not equal!')
        return
    move_to_corrected_lcses(lcses, sensors, pl_diffs)

#place_cut_sensors()
#save_corr()
#load_corr()
#recut_sensors()
