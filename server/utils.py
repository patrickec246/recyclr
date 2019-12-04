import cv2
import os
import uuid
import json
import glob
import pyexifinfo
import datetime
import base64
import random

from io import StringIO, BytesIO
from PIL import Image

from shapely.geometry import Polygon

raw_root = 'data/raw'
labaled_root = 'data/labeled'
unlabeled_root = 'data/unlabeled'

def calc_iou(poly1, poly2):
    assert(len(poly1) == 4 and len(poly2) == 4)

    a = Polygon([(p['x'], p['y']) for p in poly1])
    b = Polygon([(p['x'], p['y']) for p in poly2])

    return a.intersection(b).area / a.union(b).area

'''
 This is going to take some massaging to fine tune but this works... ok...
'''
def calculate_average_annotations(annotations, iou_thresh=.75):
    shapes = {}
    for annotation in annotations:
        shape_map = {}

        for shape in annotation['shapes']:
            label = shape['label']
            producer = shape['producer']
            qualities = shape['qualifiers']
            points = shape['points']

            if label not in shape_map:
                shape_map[label] = [points]
            else:
                shape_map[label].append(points)

        annotation_list = {}
        for label, proposed_points in shape_map.items():
            sorted_points = [sort_points_cw(point_list) for point_list in proposed_points]

            avg_points = []
            n = 0
            points_per_poly = 4

            for shape_points in sorted_points:
                for i in range(points_per_poly):
                    avg_points[i] += shape_points[i]

            if calc_iou(shape_map[label]['points'], sorted_points) >= iou_thresh:
                shapes[label].merge(sorted_points)
    return shapes

def load_frame_annotations(uuid, frame, frame_dir=unlabeled_root):
    js = []

    annotation_dir = os.path.join(frame_dir, uuid, str(frame), '*.json')

    for annotation in glob.glob(annotation_dir):
        with open(annotation, 'r') as f:
            js.append(json.loads(f.read()))

    return js

def process_video(video_path, frame_output_dir=unlabeled_root, delete_after_processing=False):
    frames = convert_video_to_frames(video_path)

    if not frames:
        return None

    if not os.path.exists(frame_output_dir):
        os.mkdir(frame_output_dir)

    dir_name = uuid.uuid4().hex
    path_name = os.path.join(frame_output_dir, dir_name)
    os.mkdir(path_name)

    for i, frame in frames:
        annotation_path = os.path.join(path_name, str(i))
        os.mkdir(annotation_path)
        frame_path = os.path.join(annotation_path, 'frame.jpg')
        cv2.imwrite(frame_path, frame)
        create_annotation_template(annotation_path, i)

    metadata = get_video_metadata(video_path)
    metadata_path = os.path.join(path_name, 'metadata.json')

    with open(metadata_path, 'w+') as f:
        f.write(json.dumps(metadata))

    return path_name

def create_annotation_template(annotation_path, frame):
    template_json = {}
    template_json['shapes'] = []

    with open(os.path.join(annotation_path, 'frame.json'), 'w+') as f:
        f.write(json.dumps(template_json))

def convert_video_to_frames(video_path):
    if not os.path.exists(video_path):
        return None

    output = []

    video = cv2.VideoCapture(video_path)
    r, frame = video.read()
    i = 0

    while r:
        output.append((i, frame))
        r, frame = video.read()
        i += 1

    return output

def get_video_metadata(file_path):
    exifinfo = pyexifinfo.get_json(file_path)[0]

    gps = exifinfo['QuickTime:GPSCoordinates']
    mktime = exifinfo['QuickTime:CreationDate']

    args = gps.split(',')
    latitude = args[0].strip()
    longitude = args[1].strip()
    elevation = args[2].strip()

    utcmktime = datetime.datetime.strptime(mktime, '%Y:%m:%d %H:%M:%S%z').strftime("%a %b %d %Y %H:%M:%S %Z")

    return {'latitude':latitude, 'longitude':longitude, 'elevation':elevation, 'creationtime':utcmktime}

def convert_img_to_base64(img_path, quality=70):
    if not os.path.exists(img_path):
        return None

    buf = BytesIO()
    img = Image.open(img_path)
    img.save(buf, format="JPEG", quality=quality)
    buf.seek(0)

    return base64.b64encode(buf.read()).decode()

def generate_image_labeling_json(last_img_uuid=None, last_frame=-1, sequential_img=False, load_server_polygons=False):
    def pick_next_image(last_img_uuid, last_frame, sequential_img, pseudo_sequential=False):
        if sequential_img:
            last_frame += 1

            if last_img_uuid is None:
                last_img_uuid = random.choice([d for d in os.listdir(unlabeled_root) if not d.startswith('.')])

            target_path = os.path.join(unlabeled_root, last_img_uuid)

            if os.path.exists(os.path.join(target_path, str(last_frame))):
                return os.path.join(target_path, str(last_frame), 'frame.jpg')
            else:
                return pick_next_image(last_img_uuid, last_frame, False, True)
        else:
            img_uuid = random.choice([d for d in os.listdir(unlabeled_root) if not d.startswith('.')])
            target_path = os.path.join(unlabeled_root, img_uuid)
            frames = sorted([d for d in os.listdir(target_path) if not d.startswith('.')])
            target_frame = frames[0] if pseudo_sequential else random.choice(frames)
            return os.path.join(target_path, target_frame, 'frame.jpg')
    
    get_frame = pick_next_image(last_img_uuid, last_frame, sequential_img)
    frame_text = convert_img_to_base64(get_frame)

    frame_no_dir = os.path.dirname(get_frame)
    uuid_dir = os.path.dirname(frame_no_dir)
    frame_no = os.path.basename(frame_no_dir)
    uuid = os.path.basename(uuid_dir)

    json_out = {'uuid' : uuid, 'frame_no' : frame_no}
    json_out['frame'] = str(frame_text)

    if load_server_polygons:
        json_out['metadata'] = calculate_average_annotations(load_frame_annotations(uuid, frame_no))

    return json.dumps(json_out)

'''
 Utils for server functionality
'''

print(generate_image_labeling_json())