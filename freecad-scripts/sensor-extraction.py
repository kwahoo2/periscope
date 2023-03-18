# SPDX-License-Identifier: Apache-2.0
# Copyright (c) 2023 Adrian Przekwas <adrian.v.przekwas@gmail.com>

# This script extract sensors and IMU placement from FreeCAD assembly and build a JSON file needed for tracker configuration
# "sensor" (imported as App::Link) should have "LCS-Diode" LCS that is placed in the center of photodiode
# "tracker-mainboard" (imported as App::Link) needs "LCS_IMU" for IMU (inertial measurement unit) placement

import FreeCAD as App
from PySide2 import QtWidgets

sensor_label = 'sensor'
tracker_base_label = 'tracker-base'
mainboard_label = 'tracker-mainboard'

doc = App.ActiveDocument

def find_diode_pl(s):
    link_pl = s.LinkPlacement
    s_doc = s.getLinkedObject().Document
    try:
        lcsdiode_pl = s_doc.getObjectsByLabel('LCS-Diode')[0].Placement
    except:
        print("No LCS-Diode found, aborting")
        return None
    lcsdiode_global_pl = link_pl * lcsdiode_pl
    return lcsdiode_global_pl

def find_imu_pl():
    try:
        mb = doc.getObjectsByLabel(mainboard_label)[0]
        link_pl = mb.LinkPlacement
        mb_doc = mb.getLinkedObject().Document
        lcsimu_pl = mb_doc.getObjectsByLabel('LCS-IMU')[0].Placement
    except:
        print(mainboard_label + "not found or does not contain LCS-IMU")
        return None
    lcsimu_global_pl = link_pl * lcsimu_pl
    return lcsimu_global_pl

def save_json():
    filename,  _  = QtWidgets.QFileDialog.getSaveFileName(QtWidgets.QApplication.activeWindow(), "Save JSON File As", "", "JSON File (*.json)")
    if filename =="":
        return
    print ("Saving: " + filename)
    json = get_json()
    outfile = open(filename,"w")
    outfile.write(json)
    outfile.close()

def get_json():
    channelMap = ""
    modelNormals = ""
    modelPoints = ""
    imuPosition = ""
    imuPlusX = ""
    imuPlusZ = ""
    try:
        sensors = doc.findObjects(Label=sensor_label)
        for idx,sens in enumerate(sensors):
            diode_pl = find_diode_pl(sens)
            if diode_pl:
                base_vec = diode_pl.Base
                mat = diode_pl.Matrix
                normal_vec = App.Vector(mat.A13, mat.A23, mat.A33)
                if (idx  > 0):
                    channelMap = channelMap + ", "
                    modelNormals = modelNormals + ",\n"
                    modelPoints = modelPoints + ",\n"
                channelMap = channelMap + str(sens.Label2) # channelMap stored in the obj destription
                modelNormals = modelNormals + "        [" + str(round(normal_vec[0], 8)) + ", " + str(round(normal_vec[1], 8)) + ", "+ str(round(normal_vec[2], 8)) + "]"
                modelPoints = modelPoints + "       [" + str(round(base_vec.x/1000, 8)) + ", " + str(round(base_vec.y/1000, 8)) + ", "+ str(round(base_vec.z/1000, 8)) + "]"

        imu_pl = find_imu_pl()
        if (imu_pl):
            base_vec = imu_pl.Base
            imuPosition = "[ " + str(round(base_vec.x/1000, 8)) + ", " +  str(round(base_vec.y/1000, 8)) + ", " + str(round(base_vec.z/1000, 8)) + " ]"
            mat = imu_pl.Matrix
            imuX = App.Vector(mat.A11, mat.A21, mat.A31)
            imuZ = App.Vector(mat.A13, mat.A23, mat.A33)
            imuPlusX = "[ " + str(round(imuX[0], 8)) + ", " + str(round(imuX[1], 8)) + ", "+ str(round(imuX[2], 8)) + "]"
            imuPlusZ = "[ " + str(round(imuZ[0], 8)) + ", " + str(round(imuZ[1], 8)) + ", "+ str(round(imuZ[2], 8)) + "]"

        json = str("{\n\
            \"manufacturer\" : \"\",\n\
            \"model_number\" : \"\",\n\
            \"device_class\" : \"controller\",\n\
            \"device_vid\" : 10462,\n\
            \"device_pid\" : 8960,\n\
            \"device_serial_number\" : \"LHR-XXXXXXXX\",\n\
            \"lighthouse_config\" : ")

        json = json + str("{\n    \"channelMap\" : [" + channelMap + "], \n    \"modelNormals\": [\n" + modelNormals + "\n    ],\n" + "    \"modelPoints\" : [\n" + modelPoints + "\n    ]\n},\n")

        json = json + str(   "\"imu\" : {\n\
            \"acc_bias\" : [ 0, 0, 0 ],\n\
            \"acc_scale\" : [ 1, 1, 1 ],\n\
            \"gyro_bias\" : [ 0, 0, 0 ],\n\
            \"gyro_scale\" : [ 1, 1, 1 ],\n\
            \"plus_x\" : " + imuPlusX + ",\n\
            \"plus_z\" : " + imuPlusZ + ",\n\
            \"position\" : " + imuPosition + "\n\
        },\n")
        json = json + get_json_tail()
        return json

    except Exception as e:
        print ("JSON: Something went wrong")
        print(e)
        return ""

def get_json_tail():
    tail = """   "render_model" : "ref_controller",
   "head" : {
      "plus_x" : [ 1, 0, 0 ],
      "plus_z" : [ 0, 0, 1 ],
      "position" : [ 0, 0, 0 ]
   },
   "revision" : 3,
   "display_edid" : [ "", "" ],
   "lens_separation" : 0.06230000033974648,
   "device" : {
      "eye_target_height_in_pixels" : 1080,
      "eye_target_width_in_pixels" : 960,
      "first_eye" : "eEYE_LEFT",
      "last_eye" : "eEYE_RIGHT",
      "num_windows" : 1,
      "persistence" : 0.01666999980807304,
      "physical_aspect_x_over_y" : 0.8000000119209290
   },
   "tracking_to_eye_transform" : [
      {
         "distortion" : {
            "center_x" : 0.0,
            "center_y" : 0.0,
            "coeffs" : [ 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 ],
            "type" : "DISTORT_DPOLY3"
         },
         "distortion_blue" : {
            "center_x" : 0.0,
            "center_y" : 0.0,
            "coeffs" : [ 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 ],
            "type" : "DISTORT_DPOLY3"
         },
         "distortion_red" : {
            "center_x" : 0.0,
            "center_y" : 0.0,
            "coeffs" : [ 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 ],
            "type" : "DISTORT_DPOLY3"
         },
         "extrinsics" : [
            [ 1.0, 0.0, 0.0, 0.03115000016987324 ],
            [ 0.0, 1.0, 0.0, 0.0 ],
            [ 0.0, 0.0, 1.0, 0.0 ]
         ],
         "grow_for_undistort" : 0.0,
         "intrinsics" : [
            [ 1.250, 0.0, 0.0 ],
            [ 0.0, 1.0, 0.0 ],
            [ 0.0, 0.0, -1.0 ]
         ],
         "undistort_r2_cutoff" : 1.50
      },
      {
         "distortion" : {
            "center_x" : 0.0,
            "center_y" : 0.0,
            "coeffs" : [ 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 ],
            "type" : "DISTORT_DPOLY3"
         },
         "distortion_blue" : {
            "center_x" : 0.0,
            "center_y" : 0.0,
            "coeffs" : [ 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 ],
            "type" : "DISTORT_DPOLY3"
         },
         "distortion_red" : {
            "center_x" : 0.0,
            "center_y" : 0.0,
            "coeffs" : [ 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0 ],
            "type" : "DISTORT_DPOLY3"
         },
         "extrinsics" : [
            [ 1.0, 0.0, 0.0, -0.03115000016987324 ],
            [ 0.0, 1.0, 0.0, 0.0 ],
            [ 0.0, 0.0, 1.0, 0.0 ]
         ],
         "grow_for_undistort" : 0.0,
         "intrinsics" : [
            [ 1.250, 0.0, 0.0 ],
            [ 0.0, 1.0, 0.0 ],
            [ 0.0, 0.0, -1.0 ]
         ],
         "undistort_r2_cutoff" : 1.50
      }
   ],
    "type" : "Lighthouse_HMD",
    "firmware_config": {
         "sensor_env_on_pin_a":"0x7FFFE000"
    }
}"""
    return tail

def run():
    save_json()

## Ensure main instructions are still called in case of manual run
if __name__ == '__main__':
    run()
