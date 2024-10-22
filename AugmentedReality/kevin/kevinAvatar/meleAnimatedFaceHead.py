# Libs
import cv2
import os
import dlib
import bpy
import math, random
from mathutils import *
import pandas as pd
import numpy as np
import pprint
import operator


resources = "Useful Resources:" + "\n" + "https://www.programcreek.com/python/example/89450/cv2.Rodrigues" + "\n" + "https://manualzz.com/doc/27121231/blender-index---blender-documentation"
print(resources)
############################# Variables #############################

# Camera
cap = cv2.VideoCapture(0)

# face detector
detector = dlib.get_frontal_face_detector()

# landmark predictor
predictor = dlib.shape_predictor(
    "C:/Users/tony/Documents/projects/objectManipulation/landmarks/shape_predictor_68_face_landmarks.dat")

# font for landmark label
font = cv2.FONT_HERSHEY_SIMPLEX

# Bools
visualization = True  # view the camera feed with annotations
face_armature = False  # move face landmarks
neck_armature = True  # move head pose by neck cSpine bone
save_renderFs = False  # capture 3D world camera view into frames

# Refresh Format
k = 2

# Dramatically poor way of relating pixels to 3d space
# need to use pnp or other technique
sensitivity = 20

# Landmark List
FACIAL_LANDMARKS_IDXS = [
    ("mouth", (48, 68)),
    ("right_eyebrow", (17, 22)),
    ("left_eyebrow", (22, 27)),
    ("right_eye", (36, 42)),
    ("left_eye", (42, 48)),
    ("nose", (27, 35)),
    ("jaw", (0, 17))
]

# Landmark List (Subset for Performance)
lm_groups = [
    ("mouth", (50, 52, 58, 56, 60, 64)),
    ("right_eyebrow", (18, 20)),
    ("left_eyebrow", (22, 24)),
    ("right_eye", (38, 40)),
    ("left_eye", (44, 48)),
    ("nose", (30, 32, 34, 36)),
    ("jaw", (2, 7, 11, 16))
]

sub = list()

for l in lm_groups:
    sub += l[1]

_lm = set(sub)

# Neck Bone for head rotation
neck_bone = ["cSpine"]

# testing focus
#_lm = lm_groups[0][1]

# Full LandMark Range
lm_full = set(list(range(1, 68)))

#_lm = lm_full
DELTA = 1
# data printer
p = pprint.PrettyPrinter(indent=1, width=80, depth=None, stream=None, compact=False)

# print the algorithm landmark setup
print("The full set of landmarks are:", lm_full)
print("The landmarks included in app:", _lm)
print("Landmark areas include:")
p.pprint(lm_groups)

############################# Definitions #############################

# change mode
def setMode(newMode):
    bpy.ops.object.mode_set(mode=newMode)
    return True


# change active object
def setActiveBone(obj):
    obj.bone.select = True
    return True


# change active object
def unSetActiveBone(obj):
    obj.bone.select = False
    return False


def force_redraw(k):
    if k == 0:
        bpy.context.scene.update()
    if k == 1:
        bpy.ops.wm.redraw_timer(type='DRAW', iterations=1)
    if k == 2:
        bpy.ops.wm.redraw_timer(type='DRAW_WIN_SWAP', iterations=1)


# translate bone
def translateBoneXYZ(armatureName, modeName, boneName, x_offset, y_offset, z_offset=0):
    # Get Armature
    arm = bpy.data.objects[armatureName]

    # POSE mode allows translation
    setMode(modeName)

    # Get Bone
    targetBone = arm.pose.bones[boneName]

    # Select Bone
    setActiveBone(targetBone)
    # targetBone.bone.select_tail=True
    # targetBone.bone.select_head=True     # Make Bone Cursor Focus
    # print("Bone, Arm, position, details", targetBone, armatureName, (x_offset/100, y_offset/100, z_offset),)

    # Translate Bone
    bpy.ops.transform.translate(  # Translate Bone
        value=(x_offset / sensitivity, y_offset / sensitivity, z_offset),
        orient_type='GLOBAL',
        orient_matrix=((1, 0, 0), (0, 1, 0), (0, 0, 1)),
        orient_matrix_type='GLOBAL',
        mirror=True,
        use_proportional_edit=False,
        proportional_edit_falloff='SMOOTH',
        proportional_size=1,
        use_proportional_connected=False,
        use_proportional_projected=False,
        release_confirm=True
    )

    unSetActiveBone(targetBone)
    # targetBone.bone.select=False
    print("ENDED", boneName)
    return True


# change bone location
def positionBoneXYZ(armatureName, modeName, x, y, z=0):
    scene = bpy.context.scene

    arm = scene.objects[armatureName]
    avatar = scene.objects["male head.obj"]
    cam = scene.objects["Camera"]

    arm = bpy.data.objects[armatureName]  # Get Armature
    setMode("POSE")  # need POSE mode to set armature bones

    for i in range(min(_lm), max(_lm) + 1):
        targetBone = arm.pose.bones["Bone." + str(i)]
        pb.location[0] = x
        pb.location[2] = y

    return True


# captures current scene as matrix
def return_frame(f):

    # capture scene as a matrix as output 
    scn = bpy.context.scene
    
    # go to frame f
    scn.frame_set(0)



    if save_renderFs:
        
        # set the filepath
        scn.render.filepath = os.path.join(
          'C:/Users/tony/Documents/projects/mimic/AugmentedReality/recordings', 
          str(f).zfill(4)
         )

        # render the current frame
        bpy.ops.render.render(write_still=False)
        
        # bpy.ops.render.opengl(animation=False, sequencer=False, write_still=False, view_context=True)

    # output the camera matrix on the current frame        
    return scn.camera.matrix_world


# loops over camera frames, move's bones ( animates face ), and captures the new frame
def animate(cycles):
    # Mode Name
    mode = "POSE"

    # Armature Name
    armature = "Armature.face"

    # Counter
    counter = 0

    # motion window
    wind = []
 

    # loop
    while counter < cycles:
        # get frame
        _, frame = cap.read()

        # get grey frame
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # detect faces
        faces = detector(gray)

        # loop through faces   
        for face in faces:

            # get all landmarks for face i
            landmarks = predictor(gray, face)

            # move the Neck Armature
            if neck_armature:
                # Position of Face
                x1 = face.left()
                y1 = face.top()
                x2 = face.right()
                y2 = face.bottom()

                # Face Position Information
                info = "Frame:" + str(counter) + " x1:" + str(x1) + " y1:" + str(y1) + " x2:" + str(x2) + " y2:" + str(y2)

                # Draw face Bounding Box
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 3)
                cv2.putText(frame, info, (x1, y1), font, .25, (255, 0, 0), 1, cv2.LINE_AA)

                # get angles of head pose [rotation and translation vectors]
                img, e_a = headPoseEstimation(frame, landmarks)
                
                if counter == 0:
                    res = tuple(map(operator.sub, tuple(e_a), (0,0,0))) 
                    e_a_old = e_a
                    
                if counter != 0:
                    res = tuple(map(operator.sub, tuple(e_a), tuple(e_a_old)))
                    e_a_old = e_a
                    res = abs(res[0])+abs(res[1])+abs(res[2])
                    print("RESULT",res)
                    if res>5:
                        rotateBoneEuler(armatureName="Armature.neck", modeName="POSE", boneName="cSpine", rotation_vector=e_a)

                # to move the Face Armature
            if face_armature:
                # initialize
                if counter == 0:
                    for n in range(min(_lm), max(_lm) + 1):
                        if n in _lm:
                            x = landmarks.part(n).x
                            y = landmarks.part(n).y
                            wind.append({"markerNumber": n, "xPos": x, "yPos": y})
                        else:
                            pass

                # provide motion change
                if counter != 0:
                    plcmnt = 1
                    for n in range(min(_lm), max(_lm) + 1):
                        if n in _lm:
                            item = list(filter(lambda marker: marker['markerNumber'] == n, wind))[0]
                            x = landmarks.part(n).x
                            y = landmarks.part(n).y
                            x_old = item["xPos"]
                            y_old = item["yPos"]
                            x_delta = x_old - x
                            y_delta = y_old - y
                            item["xPos"] = x
                            item["yPos"] = y
                            cv2.circle(frame, (x, y), 4, (255, n * 3, n * 2), -1)
                            info = "n:" + str(n) + " x:" + str(x) + " y:" + str(y)
                            cv2.putText(frame, info, (10, 10 * plcmnt), font, .25, (255, n * 3, n * 2), 1, cv2.LINE_AA)
                            plcmnt += 1
                            cv2.putText(frame, str(n), (x + 5, y), font, .5, (255, n * 3, n * 2), 1, cv2.LINE_AA)
                            
                            
                            if abs(y_delta) > 5 or abs(x_delta) > 5:
                                print ("y", y_delta, "x", x_delta) 
                                translateBoneXYZ(armatureName=armature, modeName=mode, boneName="Bone." + str(n),
                                             x_offset=x_delta / DELTA, y_offset=y_delta / DELTA, z_offset=0.00)
                       
                    
                        else:
                            pass

                            # p.pprint(wind)

        if visualization:

            # display image with opencv or any operation you like
            frame = cv2.resize(frame, (frame.shape[1]*2, frame.shape[0]*2))
            cv2.imshow("Frame", frame)

            key = cv2.waitKey(1)
            if key == 27:
                break

        counter += 1

        # Redraw the 3d view
        force_redraw(k)
        result= True
        # get rendered frame..
        # return_frame(counter)


def rotateBoneEuler(armatureName, modeName, boneName, rotation_vector):
    # Get Armature
    arm = bpy.data.objects[armatureName]

    # POSE mode allows translation
    setMode(modeName)

    # Get Bone
    targetBone = arm.pose.bones[boneName]

    # Select Bone
    setActiveBone(targetBone)

    # xv print("Rotating the bone ->", boneName)
    armFace = bpy.data.objects["Armature.face"]

    # Set rotation mode to Euler XYZ, easier to understand
    targetBone.rotation_mode = 'XYZ'
    armFace.rotation_mode = 'XYZ'

    # select axis in ['X','Y','Z']  <--bone local
    print("Rotation vector: ", rotation_vector)

    # normalize Euler Roll
    if abs(rotation_vector[2]) > 0.1:
        rotation_vector[2] = 0.1

    targetBone.rotation_euler = rotation_vector
    armFace.rotation_euler = rotation_vector
    unSetActiveBone(targetBone)
    # m=0
    # for axis in euler:
    #    angle = rotation_vector[m]
    #    m+=1
    #    print("Rotation:", axis, angle, "(radians)")
    #    targetBone.rotation_euler.rotate_axis(axis, angle)

    # Refresh 3D View
    # force_redraw(k)

    return True


def rotationMatrixToEulerAngles(R):
    sy = math.sqrt(R[0, 0] * R[0, 0] + R[1, 0] * R[1, 0])
    singular = sy < 1e-6

    if not singular:
        x = math.atan2(R[2, 1], R[2, 2])
        y = math.atan2(-R[2, 0], sy)
        z = math.atan2(R[1, 0], R[0, 0])
    else:
        x = math.atan2(-R[1, 2], R[1, 1])
        y = math.atan2(-R[2, 0], sy)
        z = 0

    euler_angles = np.array([x + 3.14, y * -1.0, z * -1.0])

    # xv print( "Euler Angles [yaw, pitch, roll]:", euler_angles )  

    return euler_angles


def headPoseEstimation(frame, landmarks):
    # "Head-and-Face Anthropometric Survey of U.S. Respirator Users"
    #  X-Y-Z with X pointing forward and Y on the left and Z up.
    # The X-Y-Z coordinates used are like the standard
    #  coordinates of ROS (robotic operative system)
    # OpenCV uses the reference usually used in computer vision: 
    #  X points to the right, Y down, Z to the front
    # The Male mean interpupillary distance is 64.7 mm (https://en.wikipedia.org/wiki/Interpupillary_distance)

    # lazy coding Image
    im = frame

    # Image dimensions in pixels
    size = im.shape

    # Landmark ID's for coordinate system reference points
    lm_nose, lm_leftMouth, lm_rightMouth = 30, 64, 60
    lm_chin, lm_leftEye, lm_rightEye = 8, 46, 37

    # 2D image points. If you change the image, you need to change vector
    landmarks_2D = np.array(
        [
            (
                landmarks.part(lm_nose).x,
                landmarks.part(lm_nose).y),  # Nose tip
            (
                landmarks.part(lm_chin).x,
                landmarks.part(lm_chin).y),  # Chin
            (
                landmarks.part(lm_leftEye).x,
                landmarks.part(lm_leftEye).y),  # Left eye left corner
            (
                landmarks.part(lm_rightEye).x,
                landmarks.part(lm_rightEye).y),  # Right eye right corne
            (
                landmarks.part(lm_leftMouth).x,
                landmarks.part(lm_leftMouth).y),  # Left Mouth corner
            (
                landmarks.part(lm_rightMouth).x,
                landmarks.part(lm_rightMouth).y)  # Right mouth corner
        ],
        dtype="double")

    # 3D model points.
    landmarks_3D = np.array(
        [
            (0.045, -.36, 3.26),  # Nose tip
            (0.08, -2.25, 2.67),  # Chin
            (1.355, 0.748, 1.87),  # Left eye left corner
            (-1.339, 0.623, 1.782),  # Right eye right corner
            (0.81, -1.39, 2.445),  # Left Mouth corner
            (-0.54, --1.34, 2.489),  # Right mouth corner
        ]
    )

    # Camera geometry
    focal_length = size[1] / 2
    center = (size[1] / 2, size[0] / 2)

    # Camera Matrix
    camera_matrix = np.array(
        [
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype="double")

    # Distances
    camera_distortion = np.zeros((4, 1))  # Assuming no lens distortion

    # Print some red dots on the image       
    for point in landmarks_2D:
        cv2.circle(frame, (int(point[0]), int(point[1])), 2, (0, 0, 255), -1)

    # retval - bool
    # rvec - Output rotation vector that, together with tvec, brings 
    # points from the world coordinate system to the camera coordinate system.
    # tvec - Output translation vector. It is the position of the world origin (SELLION) in camera co-ords

    retval, rvec, tvec = cv2.solvePnP(

        landmarks_3D,
        landmarks_2D,
        camera_matrix,
        camera_distortion

    )

    # Get as input the rotational vector
    # Return a rotational matrix
    rmat, _ = cv2.Rodrigues(rvec)

    head_pose = [
        rmat[0, 0], rmat[0, 1], rmat[0, 2], tvec[0],
        rmat[1, 0], rmat[1, 1], rmat[1, 2], tvec[1],
        rmat[2, 0], rmat[2, 1], rmat[2, 2], tvec[2],
        0.0, 0.0, 0.0, 1.0
    ]

    # euler_angles contain (pitch, yaw, roll)   
    euler_angles = rotationMatrixToEulerAngles(rmat)

    (nose_end_point2D, jacobian) = cv2.projectPoints(

        np.array([(0.0, 0.0, 10.0)]),
        rvec,
        tvec,
        camera_matrix,
        camera_distortion

    )

    # Points to plot vector normal to the landmarks_2d plane, p1->head, p2->tail
    p1 = (
        int(landmarks_2D[0][0]),
        int(landmarks_2D[0][1])
    )

    p2 = (
        int(nose_end_point2D[0][0][0]),
        int(nose_end_point2D[0][0][1])
    )

    cv2.line(im, p1, p2, (255, 0, 0), 3)
    cv2.putText(frame, "P1: " + str(p1) + "P2: " + str(p2), p1, font, .5, (255, 0, 0), 1, cv2.LINE_AA)

    # xv print( "Vector [(p1: x, y), (p2: x, y)] for Euler Calculation", p1, p2 )
    # xv print( "Camera Matrix :\n {0}".format(camera_matrix) )
    # xv print( "Rotation Vector:\n {0}".format(rvec) )
    # xv print( "Translation Vector:\n {0}".format(tvec) )

    return frame, euler_angles


def reset_face():
    for i in range(min(_lm), max(_lm) + 1):
        if i in _lm:
            arm = bpy.data.objects["Armature.face"]  # Get Armature
            setMode("POSE")  # need POSE mode to set armature bones
            pb = arm.pose.bones["Bone." + str(i)]

            pb.location[0] = 0  # x
            pb.location[1] = 0  # y
            pb.location[2] = 0  # y

    # Get Armature
    arm = bpy.data.objects["Armature.neck"]

    # POSE mode allows translation
    setMode("POSE")

    # Get Bone
    targetBone = arm.pose.bones["cSpine"]

    # Select Bone
    setActiveBone(targetBone)

    rotateBoneEuler(

        armatureName="Armature.neck",
        modeName="POSE",
        boneName="cSpine",
        rotation_vector=[0, 0, 0]

    )

    # xv print("Reset Face and Head")

    # Redraw the 3d view
    force_redraw(k)  # Refresh 3D View

    return True


############################# Execution #############################

# begin the animation
result = None
while result is None:
    try:
        animate(cycles=250)
        result=True
    except:
         pass

reset_face()

# Camera
cap.release
