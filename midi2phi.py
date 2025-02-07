import mido, sys, json, os.path, math
from pydub import AudioSegment
from PIL import Image, ImageDraw, ImageFont
import zipfile
import random, os
import struct

def midi_note2hz(note: int) -> float:
    return 440 * 2 ** ((note - 69) / 12)

def get_time(time, track):
    sec = 0.0
    beat = time
    for i, e in enumerate(bpm_list[track]):
        bpmv = e["bpm"]
        if i != len(bpm_list[track]) - 1:
            et_beat = bpm_list[track][i + 1]["time"] - e["time"]
            if beat >= et_beat:
                sec += et_beat / tpb * (60 / bpmv)
                beat -= et_beat
            else:
                sec += beat / tpb * (60 / bpmv)
                break
        else:
            sec += beat / tpb * (60 / bpmv)
    return sec

if len(sys.argv) != 3:
    print("usage: python midi2phi.py <input-path> <output-path>")
    exit(1)

with open(sys.argv[1], 'rb') as f:
    data = f.read(14)

data = struct.unpack(">4sI3H", data)

mid = mido.MidiFile(sys.argv[1], type=data[2], ticks_per_beat=data[4])

chart = {
        "formatVersion": 3,
        "offset": 0.0,
        "judgeLineList": [
            {
                "bpm": 1875,
                "judgeLineMoveEvents": [
                    {
                        "startTime": -999999,
                        "endTime": 100000000,
                        "start": 0.5,
                        "start2": 0.1,
                        "end": 0.5,
                        "end2": 0.1
                    }
                ],
                "judgeLineRotateEvents": [
                    {
                        "startTime": -999999,
                        "endTime": 100000000,
                        "start": 0,
                        "end": 0
                    }
                ],
                "judgeLineDisappearEvents": [
                    {
                        "startTime": -999999,
                        "endTime": 100000000,
                        "start": 1,
                        "end": 1,
                    }
                ],
                "speedEvents": [
                    {
                        "startTime": 0,
                        "endTime": 100000000,
                        "value": 2.2
                    }
                ],
                "notesAbove": [],
                "notesBelow": []
            }
        ]
    }

tpb = mid.ticks_per_beat

tempo = 100000000
notes = []
active_notes = {}


max_length = 0
current_time_s = 0

bpm_dict = {}
current_time = 0.
ticks_per_beat = mid.ticks_per_beat

bpm_list = []
print("获取bpm列表...")
for track in mid.tracks:
    for msg in track:
        current_time += msg.time
        if msg.type == "set_tempo":
            bpm = 60000000 / msg.tempo
            if current_time not in bpm_dict:
                bpm_dict[current_time] = bpm
    if mid.type == 2:
        bpm_list.append([{"time": time, "bpm": bpm} for time, bpm in bpm_dict.items()])


if mid.type != 2:
    bpm_list = [[{"time": time, "bpm": bpm} for time, bpm in bpm_dict.items()] for _ in mid.tracks]

print("获取音符时间...")
for i, track in enumerate(mid.tracks):
    current_time = 0.
    for msg in track:
        current_time += msg.time
        match msg.type:
            case "note_on":
                if msg.note not in active_notes and msg.velocity > 0:
                    active_notes[msg.note] = {
                        "startTime": get_time(current_time, i)*1000,
                        "note": msg.note
                    }
            case "note_off":
                if msg.note in active_notes:
                    note = active_notes.pop(msg.note)
                    notes.append({
                        "startTime": note["startTime"],
                        "endTime": get_time(current_time, i)*1000,
                        "note": note["note"]
                    })
        current_time_s = get_time(current_time, i)
        max_length = max(current_time_s*1000+1000, max_length)
print(f"谱面时长：{max_length}")

notes.sort(key=lambda x: x["startTime"])
for i, note in enumerate(notes):
    print(f"生成note {i+1}/{len(notes)}{" "*100}", end="\r")
    use_time = note["endTime"]-note["startTime"]
    one_note_use_time = 1000/midi_note2hz(note["note"])
    chart["judgeLineList"][0]["notesAbove"].extend([{
        "type": 1,
        "time": note["startTime"]+one_note_use_time*j,
        "positionX": (note["note"]-64)/128/0.05625,
        "holdTime": 0,
        "speed": 1,
        "floorPosition": 2.2 * (note["startTime"]+one_note_use_time*j) / 1000
    } for j in range(math.ceil(use_time/one_note_use_time))])
print("\n正在写入文件...")

rand = random.randint(100000000, 999999999)
music = AudioSegment.silent(duration=int(max_length))
music.export(os.path.join(sys.argv[2], f"music{rand}.wav"), format="wav")
img = Image.new("RGBA", (1920, 1080), (0, 0, 0, 255))
font = ImageFont.truetype("./font.ttf", size=56)
draw = ImageDraw.Draw(img)
draw.text((960, 540), "这是一个使用Python生成的谱面", (255, 255, 255), font=font, align="center")
img.save(os.path.join(sys.argv[2], f"bg{rand}.png"))
with zipfile.ZipFile(os.path.join(sys.argv[2], "chart.zip"), "w", zipfile.ZIP_DEFLATED) as f:
    f.writestr("0.json", json.dumps(chart).replace('"formatVersion": 3', '"formatVersion":3'))
    f.write(os.path.join(sys.argv[2], f"bg{rand}.png"), "0.png")
    f.write(os.path.join(sys.argv[2], f"music{rand}.wav"), "0.wav")
    f.writestr("info.txt", """#
Name: UK
Path: 0
Song: 0.wav
Picture: 0.png
Chart: 0.json
Level: UK  Lv.10
Composer: UK
Charter: Python 3.12
""")
os.remove(os.path.join(sys.argv[2], f"bg{rand}.png"))
os.remove(os.path.join(sys.argv[2], f"music{rand}.wav"))